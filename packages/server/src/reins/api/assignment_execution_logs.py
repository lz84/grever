"""Execution logs endpoint — split from assignment_endpoints.py"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text

from reins.common.database import get_db

router = APIRouter()

@router.get("/agents/{agent_id}/execution-logs")
def get_agent_execution_logs(
    agent_id: str, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)
):
    """获取智能体的执行记录"""
    from api.app_state import get_reins

    reins = get_reins()
    agent_info = reins.agent_registry.get_agent(agent_id)
    if not agent_info:
        db_check = db.execute(sa_text(
            "SELECT id, name, status FROM agents WHERE id = :aid"
        ), {"aid": agent_id}).fetchone()
        if not db_check:
            raise HTTPException(status_code=404, detail="Agent not found")

    query = sa_text("""
        SELECT id, task_id, agent_id, action, input, output, status, duration_ms,
               created_at, error_message, result_summary, metadata
        FROM execution_logs WHERE agent_id = :agent_id
        ORDER BY created_at DESC LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(query, {"agent_id": agent_id, "limit": limit, "offset": offset}).fetchall()

    count_query = sa_text(
        "SELECT COUNT(*) FROM execution_logs WHERE agent_id = :agent_id"
    )
    total = db.execute(count_query, {"agent_id": agent_id}).scalar()

    logs = []
    for row in rows:
        row_dict = dict(row._mapping) if hasattr(row, "_mapping") else dict(zip(
            ["id", "task_id", "agent_id", "action", "input", "output", "status",
             "duration_ms", "created_at", "error_message", "result_summary", "metadata"], row))
        for field in ["input", "output", "metadata"]:
            try:
                row_dict[field] = json.loads(row_dict[field]) if row_dict[field] else {}
            except (json.JSONDecodeError, TypeError):
                row_dict[field] = {}
        logs.append(row_dict)

    return {"success": True, "agent_id": agent_id, "logs": logs,
            "total": total, "limit": limit, "offset": offset}
