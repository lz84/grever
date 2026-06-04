"""Task CRUD helpers — shared utilities for tasks_crud endpoints."""
import json
import uuid
import logging
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from models.task import Task, TaskDependency
from models.project import Project
from persistence.tables import execution_logs

logger = logging.getLogger(__name__)


def _parse_json_list(value):
    """Parse a JSON string or list to Python list."""
    if not value:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(value, list):
        return value
    return []


def _sync_depends_on_all(task_id: str, new_deps: list, old_deps: list, db: Session, is_create: bool = False):
    """统一同步 depends_on 变更到三个地方：JSON列、next_step、关系表。"""
    removed_deps = set(old_deps) - set(new_deps)
    added_deps = set(new_deps) - set(old_deps)
    for dep_id in removed_deps:
        db.query(TaskDependency).filter_by(task_id=task_id, dependency_id=dep_id).delete()
    for dep_id in added_deps:
        parent = db.query(Task).filter(Task.id == dep_id).first()
        if not parent:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Dependency task '{dep_id}' not found")
        db.add(TaskDependency(task_id=task_id, dependency_id=dep_id))
    for dep_id in removed_deps:
        parent = db.query(Task).filter(Task.id == dep_id).first()
        if parent:
            parent_next = _parse_json_list(parent.next_step)
            parent_next = [x for x in parent_next if x != task_id]
            parent.next_step = json.dumps(parent_next) if parent_next else '[]'
    for dep_id in added_deps:
        parent = db.query(Task).filter(Task.id == dep_id).first()
        if parent:
            parent_next = _parse_json_list(parent.next_step)
            if task_id not in parent_next:
                parent_next.append(task_id)
                parent.next_step = json.dumps(parent_next)


def _probe_agent_on_assign(agent_id: str, db: Session):
    """分配任务时立即探测目标 Agent 活性。"""
    try:
        import httpx
        row = db.execute(sa_text("SELECT address, status FROM agents WHERE id = :aid"), {"aid": agent_id}).fetchone()
        if not row or not row.address:
            return
        url = f"{row.address.rstrip('/')}/health"
        try:
            resp = httpx.get(url, timeout=5)
            if 0 < resp.status_code < 500:
                now = datetime.now()
                db.execute(sa_text("""
                    UPDATE agents SET last_heartbeat = :now, status = 'online',
                        health_status = 'online', consecutive_offline_count = 0, updated_at = :now
                    WHERE id = :aid
                """), {"now": now, "aid": agent_id})
                db.commit()
                logger.info(f"[ASSIGN-PROBE] ✅ Agent {agent_id} is online (HTTP {resp.status_code} at {url})")
            else:
                logger.info(f"[ASSIGN-PROBE] ❌ Agent {agent_id} offline (HTTP {resp.status_code} at {url})")
        except httpx.ConnectError:
            logger.info(f"[ASSIGN-PROBE] ❌ Agent {agent_id} unreachable at {url}")
    except Exception as e:
        logger.warning(f"[ASSIGN-PROBE] Error probing agent {agent_id}: {e}")


def _unblock_project_dependent_tasks(completed_project_id: str, db: Session):
    """当 Project 完成时，解锁依赖它的下游 Project 中所有 waiting 任务。"""
    try:
        downstream_projects = db.execute(sa_text("SELECT id FROM projects WHERE depends_on = :pid"), {"pid": completed_project_id}).fetchall()
        for row in downstream_projects:
            child_proj_id = row[0]
            child_proj = db.query(Project).filter(Project.id == child_proj_id).first()
            if not child_proj or not child_proj.depends_on:
                continue
            dep_ids = _parse_json_list(child_proj.depends_on)
            all_deps_done = True
            for dep_id in dep_ids:
                dep_proj = db.query(Project).filter(Project.id == dep_id).first()
                if not dep_proj or dep_proj.status != 'done':
                    all_deps_done = False
                    break
            if all_deps_done:
                result = db.execute(sa_text("""
                    UPDATE tasks SET status = 'todo', blocked_reason = NULL, updated_at = :now
                    WHERE project_id = :pid AND status = 'waiting'
                """), {"pid": child_proj_id, "now": datetime.now()})
                if result.rowcount > 0:
                    logger.info(f"[PROJECT-UNBLOCK] ✅ Unblocked {result.rowcount} waiting tasks in project {child_proj_id}")
    except Exception as e:
        logger.warning(f"[PROJECT-UNBLOCK] Error unblocking downstream of {completed_project_id}: {e}")


def _check_and_update_project_done(task_id: str, project_id: str, db: Session):
    """当任务完成时，检查 Project 是否所有任务都已完成，自动更新 Project 状态。"""
    try:
        rows = db.execute(sa_text("SELECT status FROM tasks WHERE project_id = :pid"), {"pid": project_id}).fetchall()
        if not rows:
            return
        all_done = all(r[0] in ('done', 'completed') for r in rows)
        if all_done:
            db.execute(sa_text("UPDATE projects SET status = 'done', updated_at = :now WHERE id = :pid AND status != 'done'"), {"pid": project_id, "now": datetime.now()})
            db.commit()
            logger.info(f"[PROJECT-DONE] ✅ Project {project_id} all tasks done → status = 'done'")
            _unblock_project_dependent_tasks(project_id, db)
    except Exception as e:
        logger.warning(f"[PROJECT-DONE] Error checking project {project_id}: {e}")


def _unblock_downstream_tasks(completed_task_id: str, db: Session):
    """当任务完成时，自动解锁依赖它的所有 paused 下游任务。"""
    try:
        downstream = db.execute(sa_text("SELECT task_id FROM task_dependencies WHERE dependency_id = :dep_id"), {"dep_id": completed_task_id}).fetchall()
        unblocked = []
        for row in downstream:
            child_id = row[0]
            child = db.query(Task).filter(Task.id == child_id).first()
            if not child or child.status not in ('waiting', 'paused', 'todo'):
                continue
            child_deps = _parse_json_list(child.depends_on)
            if not child_deps:
                continue
            all_deps_done = True
            for dep_id in child_deps:
                dep_task = db.query(Task).filter(Task.id == dep_id).first()
                if not dep_task or dep_task.status not in ('done', 'completed'):
                    all_deps_done = False
                    break
            if all_deps_done:
                old_status = child.status
                child.status = 'todo'
                child.paused_reason = None
                child.blocked_reason = None
                db.commit()
                unblocked.append({"task_id": child_id, "old_status": old_status, "title": child.title})
                logger.info(f"[DEPENDENCY-UNBLOCK] ✅ {child_id} unlocked: {old_status} → todo")
        if unblocked:
            logger.info(f"[DEPENDENCY-UNBLOCK] Unblocked {len(unblocked)} downstream tasks of {completed_task_id}")
    except Exception as e:
        logger.warning(f"[DEPENDENCY-UNBLOCK] Error unblocking downstream of {completed_task_id}: {e}")


def _cleanup_all_on_delete(task: Task, db: Session):
    """删除任务时清理所有依赖关系。"""
    old_deps = _parse_json_list(task.depends_on)
    my_next_step = _parse_json_list(task.next_step)
    for dep_id in old_deps:
        parent = db.query(Task).filter(Task.id == dep_id).first()
        if parent:
            parent_next = _parse_json_list(parent.next_step)
            parent_next = [x for x in parent_next if x != task.id]
            parent.next_step = json.dumps(parent_next) if parent_next else '[]'
    for child_id in my_next_step:
        child = db.query(Task).filter(Task.id == child_id).first()
        if child:
            child_deps = _parse_json_list(child.depends_on)
            child_deps = [x for x in child_deps if x != task.id]
            child.depends_on = json.dumps(child_deps) if child_deps else '[]'
    db.query(TaskDependency).filter(TaskDependency.task_id == task.id).delete()
    db.query(TaskDependency).filter(TaskDependency.dependency_id == task.id).delete()
    # Clean up task-specific tables (all exist in current schema)
    required_tables = [
        'task_comments', 'task_labels',
        'task_activity_log', 'task_failure_log', 'traces',
    ]
    for table in required_tables:
        try:
            db.execute(sa_text(f"DELETE FROM {table} WHERE task_id = :tid"), {"tid": task.id})
        except Exception as e:
            logger.warning(f"[_cleanup] Failed to delete from {table}: {e}")
    # Clean up unified attachments: delete links where this task is the entity
    try:
        db.execute(sa_text("DELETE FROM attachment_links WHERE entity_type = 'task' AND entity_id = :tid"), {"tid": task.id})
    except Exception as e:
        logger.warning(f"[_cleanup] Failed to delete attachment_links: {e}")
    # Clean up human_input_requests (model has schema_json column but DB table doesn't → ORM cascade fails)
    try:
        db.execute(sa_text("DELETE FROM human_input_requests WHERE task_id = :tid"), {"tid": task.id})
    except Exception as e:
        logger.warning(f"[_cleanup] Failed to delete human_input_requests: {e}")
    try:
        db.execute(sa_text("DELETE FROM task_relations WHERE parent_task_id = :tid OR child_task_id = :tid"), {"tid": task.id})
    except Exception as e:
        logger.warning(f"[_cleanup] Failed to delete task_relations: {e}")
