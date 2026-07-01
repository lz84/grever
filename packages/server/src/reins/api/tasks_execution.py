"""Task API execution endpoints — extracted from tasks.py

Contains: report_task_progress, fail_task, get_task_failure_log, retry_task.
"""
from loguru import logger
import json
import uuid
import asyncio
import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.task import Task
from reins.common.database import get_db
from reins.scheduler.statemachine import transition_task_status
from reins.scheduler.assigner.agent_registry import AgentRegistry
from persistence.tables import task_failure_log, execution_logs
from reins.api.tasks_helpers import _get_goal_id_from_project, _update_goal_progress
from reins.scheduler.project_executor import ProjectExecutor
from reins.common.database import get_db_manager

from reins.api.tasks_models import (
    TaskProgressRequest,
    TaskProgressResponse,
    FailTaskRequest,
    FailTaskResponse,
    FailureLogEntry,
    FailureLogResponse,
    RetryRequest,
    RetryResponse,
)

router = APIRouter(tags=["tasks"])

@router.post("/{task_id}/progress", response_model=TaskProgressResponse)
def report_task_progress(task_id: str, request: TaskProgressRequest, db: Session = Depends(get_db)):
    """P1-01: Agent 主动上报任务进度"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    progress_percent = request.progress_percent
    if progress_percent is not None:
        task.progress = progress_percent / 100.0
        task.updated_at = int(datetime.now().timestamp())

    try:
        db.execute(
            execution_logs.insert().values(
                id=str(uuid.uuid4()),
                task_id=str(task_id),
                agent_id=task.assigned_agent or 'unknown',
                action='task_progress',
                input=json.dumps({
                    "progress_percent": progress_percent,
                    "current_step": request.current_step,
                    "message": request.message,
                }),
                output=json.dumps({}),
                status='success',
                duration_ms=0,
                created_at=datetime.now(),
                error_message='',
                result_summary=f"任务进度: {progress_percent}%" if progress_percent else request.message or '进度更新',
                metadata=json.dumps({"source": "task_progress_endpoint", "extra": request.metadata or {}}),
                connectivity_verified=True,
            )
        )
        db.commit()
    except Exception as e:
        logger.warning(f"[P1-01] execution_logs task_progress warning: {e}")
        db.rollback()

    return TaskProgressResponse(success=True, task_id=task_id, progress_percent=progress_percent)

@router.post("/{task_id}/fail", response_model=FailTaskResponse)
def fail_task(task_id: str, request: FailTaskRequest, db: Session = Depends(get_db)):
    """MAK-215: 任务失败 API — 重试机制"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    retry_count_base = request.retry_count if request.retry_count is not None else 0
    max_retries = request.max_retries if request.max_retries is not None else task.max_retries or 3

    transition_task_status(
        db, task, "failed",
        reason=f"Task failed: {request.error_type} - {request.error_message[:100]}",
        extra={
            "error_type": request.error_type,
            "error_message": request.error_message,
            "description": f"{task.description or ''}\n\nError: {request.error_message}",
        },
    )

    try:
        db.execute(
            execution_logs.insert().values(
                id=str(uuid.uuid4()),
                task_id=str(task_id),
                agent_id=task.assigned_agent or 'unknown',
                action='task_failed',
                input=json.dumps(request.execution_log or {}),
                output=json.dumps({}),
                status='failure',
                duration_ms=request.duration_ms or 0,
                created_at=datetime.now(),
                error_message=request.error_message,
                result_summary=f"Task failed: {request.error_type}",
                metadata=json.dumps({"source": "task_fail_endpoint"}),
                connectivity_verified=False,
            )
        )
    except Exception as e:
        logger.warning(f"[P1-01] execution_logs task_failed warning: {e}")

    delay_seconds = 30 * retry_count_base if retry_count_base > 0 else 0
    next_action = "blocked"

    if retry_count_base < max_retries:
        transition_task_status(
            db, task, "todo",
            reason=f"Auto retry ({retry_count_base + 1}/{max_retries})",
            extra={
                "assigned_agent": None,
                "retry_count": retry_count_base + 1,
            },
        )
        next_action = "retry"
    else:
        transition_task_status(
            db, task, "blocked",
            reason=f"Blocked after {retry_count_base} retries. Max retries: {max_retries}",
            extra={"blocked_reason": f"Blocked after {retry_count_base} retries. Max retries: {max_retries}"},
        )
        next_action = "blocked"

    try:
        db.execute(
            task_failure_log.insert().values(
                id=f"fail-{uuid.uuid4().hex[:12]}",
                task_id=str(task_id),
                error_type=request.error_type,
                error_message=request.error_message,
                retry_count=retry_count_base,
                max_retries=max_retries,
                timestamp=datetime.now(),
            )
        )
    except Exception as e:
        logger.warning(f"[MAK-215] Task failure log warning: {e}")

    task_goal_id = _get_goal_id_from_project(db, task.project_id)
    if task_goal_id:
        _update_goal_progress(db, task_goal_id)

    if task.assigned_agent and next_action == "blocked":
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
            logger.warning(f"[MAK-232] Task failure load update warning: {e}")

    db.commit()
    db.refresh(task)

    # ── Bug Fix: 自动重试后触发调度器重新分配 ────────────────────────
    if task.status == "todo" and task.assigned_agent is None:
        project_id = task.project_id
        task_id_str = str(task_id)
        def _trigger_fail_dispatch():
            try:
                db_m = get_db_manager()
                executor = ProjectExecutor(project_id, db_m)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(executor.tick())
                finally:
                    loop.close()
                logger.info(f"[fail_task] Dispatch triggered for {task_id_str} in project {project_id}")
            except Exception as e:
                logger.warning(f"[fail_task] Dispatch trigger failed for {task_id_str}: {e}")
        threading.Thread(target=_trigger_fail_dispatch, daemon=True).start()

    return FailTaskResponse(
        success=True,
        task_id=task_id,
        next_action=next_action,
        retry_count=retry_count_base,
        max_retries=max_retries,
        delay_seconds=delay_seconds,
    )

@router.get("/{task_id}/failure-log", response_model=FailureLogResponse)
def get_task_failure_log(task_id: str, db: Session = Depends(get_db)):
    """MAK-235: 获取任务失败历史记录"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    result = db.execute(
        task_failure_log.select()
        .where(task_failure_log.c.task_id == str(task_id))
        .order_by(task_failure_log.c.timestamp.asc())
    ).fetchall()

    failures = [
        FailureLogEntry(
            id=row.id,
            task_id=row.task_id,
            error_type=row.error_type,
            error_message=row.error_message,
            retry_count=row.retry_count,
            max_retries=row.max_retries,
            timestamp=row.timestamp.isoformat() if row.timestamp else None,
        )
        for row in result
    ]

    return FailureLogResponse(task_id=task_id, failures=failures)

@router.post("/{task_id}/retry", response_model=RetryResponse)
def retry_task(task_id: str, request: RetryRequest, db: Session = Depends(get_db)):
    """MAK-235: 手动重试任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.status not in ["failed", "blocked"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_status",
                "current_status": task.status,
                "allowed": ["failed", "blocked"],
            }
        )

    old_retry_count = task.retry_count or 0

    transition_task_status(
        db, task, "todo",
        reason=request.reason or f"Manual retry by user (previous retry_count: {old_retry_count})",
        extra={"retry_count": 0, "blocked_reason": None},
    )

    db.commit()
    db.refresh(task)

    # ── 触发调度器立即重新分配 ──
    # task 保留了 assigned_agent，tick 会直接派发
    project_id = task.project_id
    task_id_for_thread = str(task_id)
    def _trigger_dispatch():
        try:
            db_m = get_db_manager()
            executor = ProjectExecutor(project_id, db_m)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(executor.tick())
            finally:
                loop.close()
            logger.info(f"[retry_task] Dispatch triggered for {task_id_for_thread} in project {project_id}")
        except Exception as e:
            logger.warning(f"[retry_task] Dispatch trigger failed for {task_id_for_thread}: {e}")
    threading.Thread(target=_trigger_dispatch, daemon=True).start()

    return RetryResponse(
        success=True,
        task_id=task_id,
        message=f"Task {task_id} has been reset and re-queued for dispatch",
        retry_count=0,
        status=task.status,
    )