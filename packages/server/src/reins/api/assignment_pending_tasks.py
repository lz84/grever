"""Pending tasks endpoint — split from assignment_endpoints.py"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text

from reins.common.database import get_db

router = APIRouter()

@router.get("/agents/{agent_id}/pending-tasks")
def get_agent_pending_tasks(agent_id: str, db: Session = Depends(get_db)):
    """获取 Agent 的所有 pending 任务（用于调试和监控）"""
    from reins.api.assignment_services import assign_tasks_to_agent as _assign

    agent_query = sa_text("""
        SELECT id, name, capabilities, status, address, metadata,
               load, current_tasks, trigger_mode, poll_interval_seconds
        FROM agents WHERE id = :agent_id
    """)
    agent_row = db.execute(agent_query, {"agent_id": agent_id}).fetchone()
    if not agent_row:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = dict(agent_row._mapping) if hasattr(agent_row, "_mapping") else dict(
        zip(["id", "name", "capabilities", "status", "address", "metadata",
             "load", "current_tasks", "trigger_mode", "poll_interval_seconds"], agent_row))

    capabilities = []
    try:
        if agent.get("capabilities"):
            capabilities = json.loads(agent["capabilities"])
    except (json.JSONDecodeError, TypeError):
        capabilities = []

    assigned_tasks, load_limit_warning = _assign(
        agent_id=agent_id, agent_capabilities=capabilities,
        agent_current_tasks=agent.get("current_tasks", 0),
        agent_load=agent.get("load", 0), db=db,
    )

    return {
        "success": True, "agent_id": agent_id,
        "pending_tasks": assigned_tasks, "load_limit_warning": load_limit_warning,
        "total_count": len(assigned_tasks),
    }
