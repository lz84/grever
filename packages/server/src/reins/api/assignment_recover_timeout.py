"""Recover timeout endpoint — split from assignment_endpoints.py"""

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text
from datetime import datetime, timedelta

from reins.common.database import get_db

router = APIRouter()

@router.post("/internal/tasks/recover-timeout")
def recover_timeout_tasks(timeout_minutes: int = 30, db: Session = Depends(get_db)):
    """回收超时任务"""
    cutoff = datetime.now() - timedelta(minutes=timeout_minutes)

    query = sa_text("""
        SELECT id, title, assigned_agent, started_at
        FROM nexus_tasks
        WHERE status = 'in_progress' AND started_at IS NOT NULL AND started_at < :cutoff
    """)
    timeout_tasks = db.execute(query, {"cutoff": cutoff}).fetchall()

    recovered = []
    for task in timeout_tasks:
        task_id, task_title, agent_id, started_at = task
        db.execute(sa_text("""
            UPDATE nexus_tasks SET status = 'timeout', updated_at = :now,
                result_summary = '任务超时未完成，自动回收' WHERE id = :task_id
        """), {"task_id": task_id, "now": datetime.now()})

        db.execute(sa_text("""
            INSERT INTO nexus_executions (action, agent_id, task_id, status, duration_ms,
                created_at, error_message, result_summary, metadata)
            VALUES (:action, :agent_id, :task_id, :status, :duration_ms, :created_at,
                :error_message, :result_summary, :metadata)
        """), {
            "action": "task_failed", "agent_id": agent_id or "system", "task_id": task_id,
            "status": "failed", "duration_ms": 0, "created_at": datetime.now(),
            "error_message": "任务超时未完成",
            "result_summary": f"自动回收超时任务（>{timeout_minutes}分钟未完成）",
            "metadata": json.dumps({"reason": "timeout", "cutoff": str(cutoff),
                                    "source": "recover_timeout_endpoint"}),
        })

        if agent_id:
            db.execute(sa_text("""
                UPDATE nexus_agents SET current_tasks = MAX(0, current_tasks - 1),
                    updated_at = :now WHERE id = :agent_id
            """), {"agent_id": agent_id, "now": datetime.now()})

        recovered.append({"task_id": task_id, "task_title": task_title, "agent_id": agent_id})

    db.commit()
    return {"success": True, "timeout_minutes": timeout_minutes,
            "recovered_count": len(recovered), "tasks": recovered}
