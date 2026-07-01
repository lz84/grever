"""Recover timeout endpoint — split from assignment_endpoints.py"""

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from models.task import Task
from reins.common.database import get_db
from reins.scheduler.statemachine import transition_task_status

router = APIRouter()

@router.post("/internal/tasks/recover-timeout")
def recover_timeout_tasks(timeout_minutes: int = 30, db: Session = Depends(get_db)):
    """回收超时任务"""
    cutoff = datetime.now() - timedelta(minutes=timeout_minutes)

    timeout_tasks = db.query(Task).filter(
        Task.status == "in_progress",
        Task.started_at.isnot(None),
        Task.started_at < int(cutoff.timestamp()),
    ).all()

    recovered = []
    for task in timeout_tasks:
        agent_id = task.assigned_agent
        transition_task_status(
            db, task, "timeout",
            reason=f"任务超时未完成（>{timeout_minutes}分钟）",
            extra={
                "result_summary": "任务超时未完成，自动回收",
                "error_type": "timeout",
                "error_message": "任务超时未完成",
            },
        )

        recovered.append({"task_id": task.id, "task_title": task.title, "agent_id": agent_id})

    db.commit()
    return {"success": True, "timeout_minutes": timeout_minutes,
            "recovered_count": len(recovered), "tasks": recovered}
