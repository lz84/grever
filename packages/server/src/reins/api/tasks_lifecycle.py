"""Task API lifecycle endpoints — extracted from tasks.py

Contains: pause_task, resume_task, restart_task, terminate_task, takeover_task, get_task_activity.

Sprint 92 B92-2: 新增 terminate/takeover 端点 + 补充审计日志
"""
from loguru import logger
import json
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.task import Task
from reins.common.database import get_db
from persistence.tables import task_activity_log, execution_logs
from reins.common.event_bus import WorkflowEvent, get_event_bus

from reins.api.tasks_models import (
    PauseTaskResponse,
    ResumeTaskResponse,
    RestartTaskRequest,
    RestartTaskResponse,
    ActivityLogResponse,
)
from reins.api.tasks_helpers import _get_goal_id_from_project

# Pydantic models for new endpoints
from pydantic import BaseModel

class TerminateTaskRequest(BaseModel):
    """终止任务请求"""
    reason: Optional[str] = "人工终止"

class TerminateTaskResponse(BaseModel):
    """终止任务响应"""
    success: bool
    task_id: str
    old_status: str
    message: str

class TakeoverTaskRequest(BaseModel):
    """接管任务请求"""
    reason: Optional[str] = "人工接管"

class TakeoverTaskResponse(BaseModel):
    """接管任务响应"""
    success: bool
    task_id: str
    old_status: str
    new_status: str
    message: str

router = APIRouter(tags=["tasks"])

@router.post("/{task_id}/pause", response_model=PauseTaskResponse)
def pause_task(task_id: str, db: Session = Depends(get_db)):
    """Sprint 76: 将 in_progress 任务暂停"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_state_transition",
                "current_status": task.status,
                "allowed": ["in_progress"],
                "message": "只有 in_progress 状态的任务才能暂停"
            }
        )

    old_status = task.status
    now_ts = int(datetime.now().timestamp())
    now_dt = datetime.now()

    db.execute(text("""
        UPDATE tasks
        SET status = 'paused',
            paused_reason = 'human',
            started_at = NULL,
            updated_at = :now
        WHERE id = :task_id
    """), {"task_id": task_id, "now": now_ts})

    db.execute(
        task_activity_log.insert().values(
            id=f"log-{uuid.uuid4().hex[:12]}",
            task_id=str(task_id),
            old_status=old_status,
            new_status="paused",
            reason="人类主动暂停",
            timestamp=now_dt,
        )
    )

    db.commit()

    return PauseTaskResponse(success=True, task_id=task_id, status="paused", paused_reason="human")

@router.post("/{task_id}/resume", response_model=ResumeTaskResponse)
def resume_task(task_id: str, db: Session = Depends(get_db)):
    """Sprint 76: 将 paused 任务恢复到 todo"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.status != "paused":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_state_transition",
                "current_status": task.status,
                "allowed": ["paused"],
                "message": "只有 paused 状态的任务才能恢复"
            }
        )

    old_status = task.status
    now_ts = int(datetime.now().timestamp())
    now_dt = datetime.now()

    db.execute(text("""
        UPDATE tasks
        SET status = 'todo',
            paused_reason = NULL,
            started_at = NULL,
            updated_at = :now
        WHERE id = :task_id
    """), {"task_id": task_id, "now": now_ts})

    db.execute(
        task_activity_log.insert().values(
            id=f"log-{uuid.uuid4().hex[:12]}",
            task_id=str(task_id),
            old_status=old_status,
            new_status="todo",
            reason="人类主动恢复",
            timestamp=now_dt,
        )
    )

    db.commit()

    return ResumeTaskResponse(success=True, task_id=task_id, status="todo", paused_reason=None)

@router.post("/{task_id}/restart", response_model=RestartTaskResponse)
def restart_task(task_id: str, request: RestartTaskRequest = None, db: Session = Depends(get_db)):
    """重启任务: 强制切回 in_progress, 清空历史结果"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_status = task.status

    if not task.assigned_agent:
        raise HTTPException(status_code=400, detail="任务没有分配 Agent,请先重新分配再重启")

    now_ts = int(datetime.now().timestamp())
    now_dt = datetime.now()

    db.execute(text("""
        UPDATE tasks SET
            status = 'in_progress',
            started_at = :now,
            completed_at = NULL,
            result = NULL,
            result_summary = NULL,
            error_message = NULL,
            error_type = NULL,
            verification_cycle = 0,
            updated_at = :now
        WHERE id = :task_id
    """), {"now": now_ts, "task_id": task_id})

    db.execute(
        task_activity_log.insert().values(
            id=f"log-{uuid.uuid4().hex[:12]}",
            task_id=str(task_id),
            old_status=old_status,
            new_status="in_progress",
            reason=request.reason if request else "Task restarted",
            timestamp=now_dt,
        )
    )

    try:
        db.execute(
            execution_logs.insert().values(
                id=str(uuid.uuid4()),
                task_id=str(task_id),
                agent_id=task.assigned_agent,
                action='task_start',
                input=json.dumps({"old_status": old_status, "new_status": "in_progress", "reason": request.reason if request else "restarted"}),
                output=json.dumps({
                    "task_id": task_id,
                    "task_title": task.title,
                    "goal_id": _get_goal_id_from_project(db, task.project_id),
                }),
                status='success',
                duration_ms=0,
                created_at=now_dt,
                error_message='',
                result_summary='任务已重启',
                metadata=json.dumps({"source": "restart_endpoint"}),
                connectivity_verified=True,
            )
        )
    except Exception as e:
        logger.warning(f"[restart] execution_logs task_start warning: {e}")

    db.commit()

    try:
        event_bus = get_event_bus()
        event = WorkflowEvent(
            event_type="task_restarted",
            workflow_id=str(task.project_id) or "",
            step_id=str(task_id),
            data={
                "task_id": str(task_id),
                "task_title": task.title or "",
                "assigned_agent": task.assigned_agent,
                "old_status": old_status,
            },
        )
        event_bus.publish(event)
        logger.info(f"[restart] Published task_restarted event for task {task_id}")
    except Exception as e:
        logger.warning(f"[restart] Event bus warning: {e}")

    return RestartTaskResponse(
        success=True,
        task_id=task_id,
        old_status=old_status,
        new_status="in_progress",
        assigned_agent=task.assigned_agent,
    )

@router.get("/{task_id}/activity", response_model=List[ActivityLogResponse])
def get_task_activity(task_id: str, db: Session = Depends(get_db)):
    """P5-03-07: 获取 Task 状态变更历史（时间倒序）"""
    result = db.execute(
        task_activity_log.select()
        .where(task_activity_log.c.task_id == str(task_id))
        .order_by(task_activity_log.c.timestamp.desc())
    ).fetchall()

    return [
        ActivityLogResponse(
            id=row.id,
            task_id=row.task_id,
            old_status=row.old_status,
            new_status=row.new_status,
            reason=row.reason,
            actor=row.actor,
            timestamp=row.timestamp.isoformat() if row.timestamp else None,
        )
        for row in result
    ]

# ── Sprint 92 B92-2: terminate / takeover ────────────────────────

@router.post("/{task_id}/terminate", response_model=TerminateTaskResponse)
def terminate_task(task_id: str, req: TerminateTaskRequest = None, db: Session = Depends(get_db)):
    """
    Sprint 92 B92-2: 终止任务（状态 → failed，不可恢复）

    允许终止的状态: in_progress / todo / paused
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in ("in_progress", "todo", "paused"):
        raise HTTPException(
            status_code=400,
            detail=f"只有 in_progress/todo/paused 状态的任务才能终止，当前: {task.status}"
        )

    old_status = task.status
    now_ts = int(datetime.now().timestamp())
    now_dt = datetime.now()
    reason = req.reason if req else "人工终止"

    db.execute(text("""
        UPDATE tasks SET
            status = 'failed',
            error_message = :reason,
            error_type = 'human_terminated',
            started_at = NULL,
            paused_reason = NULL,
            updated_at = :now
        WHERE id = :task_id
    """), {"task_id": task_id, "now": now_ts, "reason": reason})

    db.execute(
        task_activity_log.insert().values(
            id=f"log-{uuid.uuid4().hex[:12]}",
            task_id=str(task_id),
            old_status=old_status,
            new_status="failed",
            reason=reason,
            actor="human",
            timestamp=now_dt,
        )
    )

    db.commit()

    logger.info("[lifecycle] Task %s terminated (%s → failed)", task_id, old_status)

    return TerminateTaskResponse(
        success=True,
        task_id=task_id,
        old_status=old_status,
        message=f"Task {task_id} 已终止 ({old_status} → failed)",
    )

@router.post("/{task_id}/takeover", response_model=TakeoverTaskResponse)
def takeover_task(task_id: str, req: TakeoverTaskRequest = None, db: Session = Depends(get_db)):
    """
    Sprint 92 B92-2: 人工接管任务（状态 → paused，标记 human takeover）

    允许接管的状态: in_progress
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != "in_progress":
        raise HTTPException(
            status_code=400,
            detail=f"只有 in_progress 状态的任务才能接管，当前: {task.status}"
        )

    old_status = task.status
    now_ts = int(datetime.now().timestamp())
    now_dt = datetime.now()
    reason = req.reason if req else "人工接管"

    db.execute(text("""
        UPDATE tasks SET
            status = 'paused',
            paused_reason = :reason,
            started_at = NULL,
            updated_at = :now
        WHERE id = :task_id
    """), {"task_id": task_id, "now": now_ts, "reason": reason})

    db.execute(
        task_activity_log.insert().values(
            id=f"log-{uuid.uuid4().hex[:12]}",
            task_id=str(task_id),
            old_status=old_status,
            new_status="paused",
            reason=reason,
            actor="human",
            timestamp=now_dt,
        )
    )

    db.commit()

    logger.info("[lifecycle] Task %s taken over (%s → paused)", task_id, old_status)

    return TakeoverTaskResponse(
        success=True,
        task_id=task_id,
        old_status=old_status,
        new_status="paused",
        message=f"Task {task_id} 已接管 ({old_status} → paused)",
    )