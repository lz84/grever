"""Execution logs list endpoint — /api/v1/executions"""

import json

from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text

from reins.common.database import get_db

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


@router.get("/")
def list_executions(
    agent_id: str = Query(None, description="按 Agent ID过滤"),
    task_id: str = Query(None, description="按 Task ID 过滤"),
    action: str = Query(None, description="按 action 过滤"),
    status: str = Query(None, description="按 status 过滤（success/failure）"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """列出执行记录（支持多条件过滤和分页）。"""
    conditions = []
    params = {"limit": limit, "offset": skip}
    if agent_id:
        conditions.append("agent_id = :agent_id")
        params["agent_id"] = agent_id
    if task_id:
        conditions.append("task_id = :task_id")
        params["task_id"] = task_id
    if action:
        conditions.append("action = :action")
        params["action"] = action
    if status:
        conditions.append("status = :status")
        params["status"] = status

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    count_query = sa_text(f"SELECT COUNT(*) FROM execution_logs WHERE {where_clause}")
    total = db.execute(count_query, params).scalar()

    select_query = sa_text(f"""
        SELECT id, task_id, agent_id, action, input, output, status, duration_ms,
               created_at, error_message, result_summary, metadata, connectivity_verified
        FROM execution_logs
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(select_query, params).fetchall()

    logs = []
    for row in rows:
        row_dict = dict(row._mapping) if hasattr(row, "_mapping") else dict(zip(
            ["id", "task_id", "agent_id", "action", "input", "output", "status",
             "duration_ms", "created_at", "error_message", "result_summary", "metadata",
             "connectivity_verified"], row))
        for field in ["input", "output", "metadata"]:
            try:
                row_dict[field] = json.loads(row_dict[field]) if row_dict[field] else {}
            except (json.JSONDecodeError, TypeError):
                row_dict[field] = {}
        logs.append(row_dict)

    return {"items": logs, "total": total, "skip": skip, "limit": limit}