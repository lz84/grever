"""
任务分配操作（从 task_assigner.py 拆分）

包含：
- query_pending_tasks(): 查询所有待分配任务
- assign_pending_tasks_impl(): 分配待处理任务的实现
- redistribute_recovered_impl(): 重新分配失败任务的实现
"""
from loguru import logger
import json

from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from models.task import Task
from models.agent import Agent
from reins.scheduler.assigner.task_assigner_helpers import (
    _assign_agent,
    _assign_verifier,
)


# ── 查询待分配任务 ─────────────────────────────────────────

def query_pending_tasks(session: Session) -> List[Task]:
    """
    查询所有待分配任务（ORM + SQLAlchemy Core 混合）

    条件：
    - status IN ('todo', 'pending', 'waiting')
    - assigned_agent IS NULL OR assigned_agent 离线 OR 已有执行者在线但仍为 todo
    - needs_verification=True 但 verifier 未分配
    - Task 级别依赖全部完成
    - Project 级别依赖链全部 completed
    - 按 priority + created_at 排序
    """
    # 例外：ORM 无法表达 SQLite json_each 展开 depends_on 数组做 JOIN 聚合检查
    raw_query = text("""
        SELECT DISTINCT t.id
        FROM tasks t
        WHERE t.status IN ('todo', 'pending', 'waiting')
          AND (
              t.assigned_agent IS NULL
              OR EXISTS (
                  SELECT 1 FROM agents a
                  WHERE a.id = t.assigned_agent
                    AND a.health_status != 'online'
              )
              OR (
                  t.assigned_agent IS NOT NULL
                  AND EXISTS (
                      SELECT 1 FROM agents a2
                      WHERE a2.id = t.assigned_agent
                        AND a2.health_status = 'online'
                  )
              )
              OR (t.needs_verification = 1 AND t.verifier_agent_id IS NULL)
          )
          AND NOT EXISTS (
              SELECT 1 FROM task_dependencies td
              JOIN tasks dep ON td.dependency_id = dep.id
              WHERE td.task_id = t.id AND dep.status != 'done'
          )
          AND NOT EXISTS (
              SELECT 1
              FROM projects parent_proj, json_each(parent_proj.depends_on) AS dep_elem
              JOIN projects dep_proj ON dep_proj.id = dep_elem.value
              WHERE parent_proj.id = t.project_id
                AND parent_proj.depends_on IS NOT NULL
                AND parent_proj.depends_on != 'null'
                AND parent_proj.depends_on != '[]'
                AND dep_proj.status != 'completed'
          )
        ORDER BY
            CASE t.priority
                WHEN 'critical' THEN 0
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            t.created_at ASC
    """)
    result = session.execute(raw_query)
    task_ids = [row[0] for row in result.fetchall()]

    if not task_ids:
        return []

    # 再次用 ORM 按 ID 列表顺序取回（保持排序）
    tasks = session.query(Task).filter(Task.id.in_(task_ids)).all()
    id_order = {tid: idx for idx, tid in enumerate(task_ids)}
    tasks.sort(key=lambda t: id_order.get(t.id, 999))
    return tasks


# ── 分配待处理任务 ──────────────────────────────────────────

def assign_pending_tasks_impl(db_manager) -> Dict[str, Any]:
    """分配待处理任务：匹配引擎/负载选择 + 分配执行者 + 分配验证者"""
    assigned_count = 0
    session = db_manager.get_session()
    try:
        pending_tasks = query_pending_tasks(session)
        if not pending_tasks:
            session.commit()
            return {"assigned_count": 0}

        # 缓存 Agent max_concurrent_tasks（避免重复查询）
        agent_max: Dict[str, int] = {}

        def _available_slots(agent_id: str) -> int:
            """实时从 tasks 表算可用 slot"""
            if agent_id not in agent_max:
                ag = session.query(Agent).filter(Agent.id == agent_id).first()
                agent_max[agent_id] = ag.max_concurrent_tasks if ag else 0
            mx = agent_max.get(agent_id, 0)
            actual = session.query(func.count(Task.id)).filter(
                Task.assigned_agent == agent_id,
                Task.status.in_(['in_progress', 'running'])
            ).scalar() or 0
            return max(0, mx - actual)

        from reins.scheduler.load_calculator import update_agent_load

        for task in pending_tasks:
            task_id = task.id
            assigned_agent_raw = task.assigned_agent
            cap_tags_raw = task.capability_tags
            needs_verification = task.needs_verification
            existing_verifier = task.verifier_agent_id

            # 解析 capability_tags
            capability_tags = {}
            if cap_tags_raw:
                try:
                    capability_tags = json.loads(cap_tags_raw) if isinstance(cap_tags_raw, str) else cap_tags_raw
                except Exception:
                    pass

            # 用匹配引擎选 Agent（全满则 fallback）
            chosen_agent_id = None
            if capability_tags:
                try:
                    from reins.scheduler.assigner.agent_matcher import match_for_task
                    for match in match_for_task(capability_tags):
                        if _available_slots(match["agent_id"]) > 0:
                            chosen_agent_id = match["agent_id"]
                            break
                except Exception as e:
                    logger.warning(f"[TaskAssigner] match_for_task failed: {e}")

            if not chosen_agent_id:
                chosen_agent_id = assigned_agent_raw or _assign_agent(session)
            if not chosen_agent_id:
                continue

            now_ts = int(datetime.now().timestamp())

            # Sprint 85: 分配验证者
            verifier_agent_id = existing_verifier
            if needs_verification and not existing_verifier:
                verifier_agent_id = _assign_verifier(session, chosen_agent_id, capability_tags)
                if verifier_agent_id:
                    logger.info(f"[TaskAssigner] Assigned verifier {verifier_agent_id} for task {task_id}")

            # 分配任务
            filters = [Task.id == task_id, Task.status.in_(['todo', 'pending', 'waiting'])]
            if not assigned_agent_raw:
                session.query(Task).filter(*filters).update({
                    "assigned_agent": chosen_agent_id,
                    "verifier_agent_id": verifier_agent_id,
                    "updated_at": now_ts,
                })
                assigned_count += 1
            elif verifier_agent_id:
                session.query(Task).filter(*filters).update({
                    "verifier_agent_id": verifier_agent_id,
                    "updated_at": now_ts,
                })
                assigned_count += 1
                logger.info(f"[TaskAssigner] Assigned verifier {verifier_agent_id} for existing task {task_id}")

        # 批量更新 Agent current_tasks + load
        for aid in agent_max:
            actual = session.query(func.count(Task.id)).filter(
                Task.assigned_agent == aid,
                Task.status.in_(['in_progress', 'running'])
            ).scalar() or 0
            session.query(Agent).filter(Agent.id == aid).update({
                "current_tasks": actual,
                "updated_at": datetime.now(),
            })
            update_agent_load(session, aid)

        session.commit()
        return {"assigned_count": assigned_count}
    except Exception as e:
        logger.error(f"[TaskAssigner] assign_pending_tasks error: {e}")
        session.rollback()
        return {"assigned_count": 0}
    finally:
        session.close()


# ── 重新分配失败任务 ────────────────────────────────────────

def redistribute_recovered_impl(db_manager) -> Dict[str, Any]:
    """
    重新分配 retry_count > 0 的任务

    逻辑：
    1. 找到 retry_count > 0 的待处理任务
    2. 检查 max_retries (默认 3)
    3. 重新分配给负载最低的在线 Agent
    """
    redistributed_count = 0
    max_retries = 3
    session = db_manager.get_session()

    try:
        # 注：原代码用 recovery_count，但 Task 模型实际字段为 retry_count
        tasks = (
            session.query(Task)
            .filter(Task.retry_count > 0)
            .filter(Task.retry_count < max_retries)
            .filter(Task.status.in_(['todo', 'pending']))
            .all()
        )

        from reins.scheduler.load_calculator import update_agent_load

        for task in tasks:
            task_id = task.id
            assigned_agent = task.assigned_agent

            # 获取负载最低的在线 Agent
            new_agent_id = _assign_agent(session)
            if not new_agent_id:
                break

            now_ts = int(datetime.now().timestamp())

            # 更新任务
            session.query(Task).filter(Task.id == task_id).update({
                "assigned_agent": new_agent_id,
                "retry_count": Task.retry_count + 1,
                "started_at": None,
                "status": 'todo',
                "paused_reason": None,
                "updated_at": now_ts,
            })

            # 更新新 Agent 的 current_tasks
            actual_new = session.query(func.count(Task.id)).filter(
                Task.assigned_agent == new_agent_id,
                Task.status.in_(['in_progress', 'running'])
            ).scalar()
            session.query(Agent).filter(Agent.id == new_agent_id).update({
                "current_tasks": actual_new or 0,
                "updated_at": datetime.now(),
            })
            update_agent_load(session, new_agent_id)

            # 如果原 Agent 存在，重新算其 current_tasks
            if assigned_agent:
                actual_old = session.query(func.count(Task.id)).filter(
                    Task.assigned_agent == assigned_agent,
                    Task.status.in_(['in_progress', 'running'])
                ).scalar()
                session.query(Agent).filter(Agent.id == assigned_agent).update({
                    "current_tasks": actual_old or 0,
                    "updated_at": datetime.now(),
                })
                update_agent_load(session, assigned_agent)

            redistributed_count += 1

        session.commit()
        return {"redistributed_count": redistributed_count}
    except Exception as e:
        logger.error(f"[TaskAssigner] redistribute_recovered error: {e}")
        session.rollback()
        return {"redistributed_count": 0}
    finally:
        session.close()
