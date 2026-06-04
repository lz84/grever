"""
Security Endpoints Router — 安全中心告警/审计日志别名
从 server.py 内联端点提取（2026-05-14）
"""
from loguru import logger
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import text

from api.app_state import get_db_manager

router = APIRouter(prefix="/api/v1", tags=["security"])

@router.get("/security/alerts")
def security_list_alerts(
    level: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
):
    """安全中心 - 告警列表"""
    skip = max(0, int(skip or 0))
    limit = max(1, min(200, int(limit or 50)))
    db = get_db_manager()
    with db.engine.connect() as conn:
        conditions = []
        params = {"limit": limit, "offset": skip}
        if level:
            conditions.append("level = :level")
            params["level"] = level
        if status:
            conditions.append("status = :status")
            params["status"] = status
        where = " AND ".join(conditions) if conditions else "1=1"
        total = conn.execute(text(f"SELECT count(*) FROM alerts WHERE {where}"), params).fetchone()[0]
        rows = conn.execute(text(
            f"SELECT * FROM alerts WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
            params).fetchall()
    return {
        "total": total,
        "alerts": [{"id": r[0], "title": r[1], "description": r[2], "level": r[3],
                     "category": r[4], "status": r[5], "source": r[6], "created_at": r[12]} for r in rows],
    }

@router.get("/security/audit/logs")
def security_list_audit_logs(skip: int = 0, limit: int = 50):
    """安全中心 - 审计日志"""
    skip = max(0, int(skip or 0))
    limit = max(1, min(200, int(limit or 50)))
    db = get_db_manager()
    with db.engine.connect() as conn:
        total = conn.execute(text("SELECT count(*) FROM audit_logs"), {}).fetchone()[0]
        rows = conn.execute(text(
            f"SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT {limit} OFFSET {skip}"),
            {}).fetchall()
    return {
        "total": total,
        "logs": [{"id": r[0], "operation": r[1], "resource_type": r[2],
                   "resource_id": r[3], "operator": r[4], "created_at": r[7]} for r in rows],
    }
