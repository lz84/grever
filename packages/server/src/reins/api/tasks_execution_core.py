"""Task API execution core logic — extracted from tasks.py

Contains helper functions for complete_task: _write_execution_log, _handle_human_input,
_handle_scenario_feedback, _handle_agent_load_on_complete, _auto_complete_project,
_publish_task_completed_event, _sprint74_capture_and_compare.
"""
from loguru import logger
import json
import uuid
import re
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from models.task import Task
from models.goal import Goal
from models.project import Project
from models.scenario import Scenario
from persistence.tables import task_activity_log, execution_logs
from reins.common.event_bus import WorkflowEvent, get_event_bus
from reins.scheduler.assigner.agent_registry import AgentRegistry
from reins.scheduler.result_verifier import ResultVerifier

from reins.api.tasks_helpers import (
    _get_goal_id_from_project,
    _update_goal_progress,
    _parse_agent_result,
    _create_human_input_request,
    _evaluate_scenario_evolution,
)

def _write_execution_log(task, request, db):
    """Write execution_logs for task_complete."""
    try:
        db.execute(
            execution_logs.insert().values(
                id=str(uuid.uuid4()),
                task_id=str(task.id),
                agent_id=task.assigned_agent or 'unknown',
                action='task_complete',
                input=json.dumps(request.execution_log or {}),
                output=json.dumps(request.output or {}),
                status='success',
                duration_ms=request.duration_ms or 0,
                created_at=datetime.now(),
                error_message='',
                result_summary=str(request.result)[:1000] if request.result else '',
                metadata=json.dumps({"source": "task_complete_endpoint", "validation_passed": True}),
                connectivity_verified=True,
            )
        )
    except Exception as e:
        logger.warning(f"[P1-01] execution_logs task_complete warning: {e}")

def _handle_human_input(task, request, old_status, db):
    """Detect human input needs and create request + notify."""
    human_input_data = _parse_agent_result(request.result)

    if human_input_data and human_input_data.get("needs_human_input"):
        human_input_request = _create_human_input_request(task.id, human_input_data, db)
        if human_input_request:
            task.status = "waiting_human"
            task.updated_at = datetime.now()

            db.execute(
                task_activity_log.insert().values(
                    id=f"log-{uuid.uuid4().hex[:12]}",
                    task_id=str(task.id),
                    old_status=old_status,
                    new_status="waiting_human",
                    reason=f"Waiting for human input: {human_input_request.title}",
                    timestamp=datetime.now(),
                )
            )

            logger.info(f"[T2] Task {task.id} set to 'waiting_human' status due to human input requirement")

            try:
                from services.feishu_notification import notify_task_waiting_human
                task_link = f"http://localhost:8000/api/v1/tasks/{task.id}"
                submit_link = f"http://localhost:8000/api/v1/human-input/{human_input_request.id}/submit"
                notify_task_waiting_human(
                    task_id=task.id,
                    task_title=human_input_request.title,
                    task_description=human_input_request.description or task.title,
                    user_email=None,
                    task_link=task_link,
                    submit_link=submit_link,
                )
            except ImportError:
                logger.info(f"[T2] 飞书通知服务未安装,跳过通知 for task {task.id}")
            except Exception as e:
                logger.info(f"[T2] 发送飞书通知时发生错误: {e}")

def _handle_scenario_feedback(task, request, db):
    """Trigger scenario library feedback and evolution."""
    scenario_feedback_triggered = False
    scenario_evolution_result = None

    task_category = getattr(task, 'category', None)
    if task_category and task.status == "done":
        try:
            scenario_id = None

            if hasattr(task, 'metadata') and task.metadata:
                try:
                    meta = json.loads(task.metadata) if isinstance(task.metadata, str) else task.metadata
                    scenario_id = meta.get('scenario_id')
                except Exception:
                    pass

            if not scenario_id and task.description:
                match = re.search(r'scenario_id:\s*([^\s,]+)', task.description)
                if match:
                    scenario_id = match.group(1)

            if not scenario_id:
                scenario_id = task_category

            if scenario_id:
                scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
                if scenario:
                    scenario.total_executions = (scenario.total_executions or 0) + 1
                    if task.status == "done":
                        scenario.success_count = (scenario.success_count or 0) + 1
                    else:
                        scenario.failed_count = (scenario.failed_count or 0) + 1

                    new_duration = request.duration_ms or 0
                    if scenario.avg_duration_ms and scenario.total_executions > 1:
                        scenario.avg_duration_ms = (
                            (scenario.avg_duration_ms * (scenario.total_executions - 1) + new_duration)
                            / scenario.total_executions
                        )
                    else:
                        scenario.avg_duration_ms = new_duration

                    scenario.success_rate = (
                        (scenario.success_count / scenario.total_executions * 100)
                        if scenario.total_executions > 0 else 0
                    )
                    scenario.usage_count = (scenario.usage_count or 0) + 1

                    exec_log_raw = scenario.execution_log
                    if exec_log_raw and isinstance(exec_log_raw, str):
                        try:
                            exec_log = json.loads(exec_log_raw)
                        except Exception:
                            exec_log = []
                    elif exec_log_raw and isinstance(exec_log_raw, list):
                        exec_log = exec_log_raw
                    else:
                        exec_log = []

                    exec_log.append({
                        "timestamp": datetime.now().isoformat(),
                        "status": task.status,
                        "duration_ms": new_duration,
                        "success": task.status == "done",
                    })
                    scenario.execution_log = json.dumps(exec_log)

                    evolution_result = _evaluate_scenario_evolution(db, scenario, task.status == "done")
                    scenario_evolution_result = evolution_result

                    scenario_feedback_triggered = True
        except Exception as e:
            logger.warning(f"[MAK-215] Scenario feedback warning: {e}")

    return scenario_feedback_triggered, scenario_evolution_result

def _handle_agent_load_on_complete(task, db):
    """Update agent load after task completion."""
    if task.assigned_agent:
        try:
            agent_registry = AgentRegistry()
            current_tasks_query = text("""
                SELECT
                    (SELECT current_tasks FROM agents WHERE id = :agent_id) - 1 AS new_current_tasks,
                    (SELECT max_concurrent_tasks FROM agents WHERE id = :agent_id) AS max_concurrent_tasks
            """)
            result = db.execute(current_tasks_query, {"agent_id": task.assigned_agent}).fetchone()
            if result:
                new_current_tasks = max(0, result[0]) if result[0] else 0
                max_concurrent_tasks = result[1] if result[1] else 5
                agent_registry.update_load_withCalculation(
                    agent_id=task.assigned_agent,
                    current_tasks=new_current_tasks,
                )
        except Exception as e:
            logger.warning(f"[MAK-232] Task completion load update warning: {e}")

def _auto_complete_project(db, task):
    """Auto-complete project when all tasks are done, and activate next draft project."""
    from sqlalchemy import text as sa_text
    project = db.query(Project).filter(Project.id == task.project_id).first()
    if project and project.status not in ("completed", "on_hold"):
        total = db.query(Task).filter(Task.project_id == task.project_id).count()
        done = db.query(Task).filter(Task.project_id == task.project_id, Task.status == "done").count()
        if total > 0 and total == done:
            project.status = "completed"
            project.updated_at = datetime.now()
            db.execute(
                task_activity_log.insert().values(
                    id=f"log-{uuid.uuid4().hex[:12]}",
                    task_id=None,
                    old_status="active",
                    new_status="completed",
                    reason=f"项目自动完成:所有 {total} 个任务均已完成",
                    timestamp=datetime.now(),
                )
            )
            db.flush()

            # 【Sprint 89 修复】激活下一个 draft 工程
            goal_id = project.goal_id
            if goal_id:
                next_proj = db.execute(sa_text(
                    "SELECT id FROM projects WHERE goal_id = :gid AND status = 'draft' ORDER BY created_at ASC LIMIT 1"
                ), {"gid": goal_id}).fetchone()
                if next_proj:
                    npid = next_proj[0]
                    db.execute(sa_text("UPDATE projects SET status = 'active', updated_at = :now WHERE id = :pid"),
                               {"now": datetime.now(), "pid": npid})
                    logger.info(f"[Scheduler] Project {npid}: auto-activated (next draft project)")

def _publish_task_completed_event(task, task_goal_id, request, validation_passed, validation_reason):
    """Publish task_completed event."""
    try:
        event_bus = get_event_bus()
        event = WorkflowEvent(
            event_type="task_completed",
            workflow_id=str(task_goal_id) if task_goal_id else "",
            step_id=str(task.id),
            data={
                "task_id": str(task.id),
                "task_title": task.title or "",
                "workflow_id": str(task_goal_id) if task_goal_id else "",
                "status": task.status,
                "result": request.result,
                "duration_ms": request.duration_ms,
                "validation_passed": validation_passed,
                "validation_reason": validation_reason if not validation_passed else None
            },
        )
        event_bus.publish(event)
        logger.info(f"[MAK-233] Published task_completed event for task {task.id}")
    except Exception as e:
        logger.info(f"[MAK-233] Failed to publish task_completed event: {e}")

def _sprint74_capture_and_compare(db, task, request, task_goal_id):
    """Sprint 74: Auto-capture solution for exploration/optimization goals."""
    try:
        goal_mode_row = db.execute(
            text("SELECT mode, title FROM goals WHERE id = :id"),
            {"id": task_goal_id}
        ).mappings().fetchone()

        if goal_mode_row and goal_mode_row.get("mode") in ("exploration", "optimization"):
            try:
                params_data = json.loads(request.result)
                parameters = params_data if isinstance(params_data, dict) else {"raw": str(params_data)}
            except Exception:
                parameters = {"raw": request.result[:200]}

            goal_title = goal_mode_row.get("title", "Goal")
            current_round = db.execute(
                text("SELECT COALESCE(MAX(round), 0) + 1 FROM solutions WHERE goal_id = :gid"),
                {"gid": task_goal_id}
            ).fetchone()[0]
            short_title = goal_title[:10] if goal_title else "sol"
            sol_name = f"sol-{current_round}-{short_title}"
            score = request.confidence if request.confidence is not None else len(request.result) / 10.0
            sol_id = f"sol-{uuid.uuid4().hex[:12]}"
            now_iso = datetime.utcnow().isoformat()

            db.execute(text("""
                INSERT INTO solutions (id, goal_id, round, name, status, parameters, score,
                                       task_ids, created_at, updated_at)
                VALUES (:id, :gid, :round, :name, 'compliant', :params, :score,
                        :task_ids, :now, :now)
            """), {
                "id": sol_id, "gid": task_goal_id, "round": current_round,
                "name": sol_name, "params": json.dumps(parameters, ensure_ascii=False),
                "score": score, "task_ids": json.dumps([task.id], ensure_ascii=False),
                "now": now_iso,
            })
            db.commit()

            sols = db.execute(text("""
                SELECT id, score, is_optimal, round FROM solutions
                WHERE goal_id = :gid ORDER BY round ASC
            """), {"gid": task_goal_id}).mappings().fetchall()
            if len(sols) >= 2:
                best = max(sols, key=lambda s: s.get("score") or 0)
                db.execute(text("UPDATE solutions SET is_optimal=0 WHERE goal_id=:gid"), {"gid": task_goal_id})
                db.execute(text("UPDATE solutions SET is_optimal=1 WHERE id=:id"), {"id": best.get("id")})
                db.commit()
                logger.info(f"[Sprint 74] Optimal updated: {best.get('id')}")
    except Exception as e:
        logger.warning(f"[Sprint 74] Auto-capture warning: {e}")