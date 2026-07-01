"""Task API state management endpoints — extracted from tasks.py

Contains: batch_update_status, update_task_status, block_task, unblock_task, get_task_statuses.
"""
from loguru import logger
import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from models.task import Task, TaskResponse
from reins.common.database import get_db
from reins.scheduler.statemachine import transition_task_status, batch_transition_task_status, VALID_TRANSITIONS
from persistence.tables import execution_logs

from reins.api.tasks_models import (
    BatchStatusUpdate,
    BatchUpdateResponse,
    TaskStatusUpdateRequest,
    BlockTaskRequest,
    UnblockTaskRequest,
    TaskStatusItem,
    TaskAssignRequest,
)
from reins.api.tasks_helpers import _get_goal_id_from_project

router = APIRouter(tags=["tasks"])

@router.patch("/batch", response_model=BatchUpdateResponse)
def batch_update_status(batch: BatchStatusUpdate, db: Session = Depends(get_db)):
    """
    P5-03-05: 批量状态变更。
    一次性更新多个 Task 的状态,非法转换的任务会被跳过并记录在 failed 中。
    """
    tasks = []
    for task_id in batch.task_ids:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            tasks.append(task)
        else:
            pass  # handled below via comparison

    if not tasks:
        return BatchUpdateResponse(updated=0, failed=[{"task_id": tid, "error": "Task not found"} for tid in batch.task_ids])

    extra = {}
    if batch.status == "blocked":
        extra["blocked_reason"] = batch.reason or "Blocked by batch operation"
    elif batch.status in ("todo", "in_progress"):
        extra["blocked_reason"] = None

    success, failed = batch_transition_task_status(
        db, tasks, batch.status,
        reason=batch.reason or "Batch status update",
        extra=extra if extra else None,
    )

    # Add not-found tasks to failed list
    found_ids = {t.id for t in tasks}
    for task_id in batch.task_ids:
        if task_id not in found_ids:
            failed.append({"task_id": task_id, "error": "Task not found"})

    # Log execution_logs for in_progress transitions
    for task in success:
        if batch.status == "in_progress":
            db.execute(
                execution_logs.insert().values(
                    id=str(uuid.uuid4()),
                    task_id=str(task.id),
                    agent_id=task.assigned_agent or '',
                    action='task_start',
                    input=json.dumps({"old_status": "todo", "new_status": "in_progress"}),
                    output=json.dumps({
                        "task_id": task.id,
                        "task_title": task.title,
                        "goal_id": _get_goal_id_from_project(db, task.project_id),
                    }),
                    status='success',
                    duration_ms=0,
                    created_at=None,
                    error_message='',
                    result_summary='任务已开始',
                    metadata=json.dumps({"source": "batch_update_status"}),
                    connectivity_verified=True,
                )
            )

    return BatchUpdateResponse(updated=len(success), failed=failed)

@router.patch("/{task_id}/status", response_model=TaskResponse)
def update_task_status(task_id: str, request: TaskStatusUpdateRequest, db: Session = Depends(get_db)):
    """P5-05: 更新任务状态"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    try:
        transition_task_status(
            db, task, request.status,
            reason=f"Status update: {task.status} → {request.status}",
        )
        db.commit()
        db.refresh(task)
        return task.to_dict()
    except Exception as e:
        if "Invalid status transition" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_state_transition", "message": str(e)},
            )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{task_id}/assign", response_model=TaskResponse)
def assign_task(task_id: str, request: TaskAssignRequest, db: Session = Depends(get_db)):
    """Assign a task to an agent. Sets assigned_agent on the task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Validate agent exists
    from models.agent import Agent
    agent = db.query(Agent).filter(Agent.id == request.agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    try:
        task.assigned_agent = request.agent_id
        task.updated_at = db.commit()
        db.refresh(task)
        return task.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{task_id}/block", response_model=TaskResponse)
def block_task(task_id: str, request: BlockTaskRequest, db: Session = Depends(get_db)):
    """P5-03-06: 阻塞任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    try:
        transition_task_status(
            db, task, "blocked",
            reason=request.reason or "Blocked",
            extra={"blocked_reason": request.reason},
        )
        db.commit()
        db.refresh(task)
        return task.to_dict()
    except Exception as e:
        if "Invalid status transition" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_state_transition", "message": str(e)},
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.patch("/{task_id}/unblock", response_model=TaskResponse)
def unblock_task(task_id: str, request: UnblockTaskRequest, db: Session = Depends(get_db)):
    """P5-03-06: 解锁任务(blocked → todo)"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.status != "blocked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Task is not blocked", "current_status": task.status}
        )

    try:
        transition_task_status(
            db, task, "todo",
            reason=request.reason or "Unblocked",
            extra={"blocked_reason": None},
        )
        db.commit()
        db.refresh(task)
        return task.to_dict()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/statuses", response_model=list[TaskStatusItem])
def get_task_statuses():
    """获取所有可选任务状态（前端下拉框统一使用此接口）"""
    return [
        TaskStatusItem(value="todo", label="待处理", category="db", color="blue"),
        TaskStatusItem(value="in_progress", label="进行中", category="db", color="yellow"),
        TaskStatusItem(value="done", label="已完成", category="db", color="green"),
        TaskStatusItem(value="failed", label="失败", category="db", color="red"),
        TaskStatusItem(value="timeout", label="已超时", category="db", color="gray"),
        TaskStatusItem(value="paused", label="已暂停", category="db", color="orange"),
        TaskStatusItem(value="review_needed", label="待审核", category="workflow", color="purple"),
        TaskStatusItem(value="verifying", label="验证中", category="workflow", color="purple"),
        TaskStatusItem(value="waiting_human", label="等待人工", category="workflow", color="purple"),
        TaskStatusItem(value="disputed", label="争议中", category="workflow", color="red"),
        TaskStatusItem(value="blocked", label="阻塞中", category="workflow", color="gray"),
    ]