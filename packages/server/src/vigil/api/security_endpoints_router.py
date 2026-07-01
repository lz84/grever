"""
Security Endpoints Router — 安全中心告警/审计日志别名
从 server.py 内联端点提取（2026-05-14）
"""
from loguru import logger
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from api.app_state import get_db_manager

router = APIRouter(prefix="/api/v1", tags=["security"])

# We need to create ORM models for alerts and audit_logs since they don't exist yet
# Using raw SQLAlchemy Core for these tables as they lack ORM models
from sqlalchemy import Table, Column, String, Integer, DateTime, MetaData, select

metadata = MetaData()
alerts_table = Table('alerts', metadata,
    Column('id', String(36), primary_key=True),
    Column('title', String(255)),
    Column('description', String(1000)),
    Column('level', String(20)),
    Column('category', String(50)),
    Column('status', String(20)),
    Column('source', String(100)),
    Column('created_at', DateTime),
)

audit_logs_table = Table('audit_logs', metadata,
    Column('id', String(36), primary_key=True),
    Column('operation', String(100)),
    Column('resource_type', String(50)),
    Column('resource_id', String(100)),
    Column('operator', String(100)),
    Column('created_at', DateTime),
)

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
        if level:
            conditions.append(alerts_table.c.level == level)
        if status:
            conditions.append(alerts_table.c.status == status)
        
        query = select(alerts_table)
        count_query = select(func.count()).select_from(alerts_table)
        
        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)
        
        total = conn.execute(count_query).scalar()
        rows = conn.execute(
            query.order_by(alerts_table.c.created_at.desc()).limit(limit).offset(skip)
        ).fetchall()
    return {
        "total": total,
        "alerts": [{"id": r[0], "title": r[1], "description": r[2], "level": r[3],
                     "category": r[4], "status": r[5], "source": r[6], "created_at": r[7]} for r in rows],
    }

@router.get("/security/audit/logs")
def security_list_audit_logs(skip: int = 0, limit: int = 50):
    """安全中心 - 审计日志"""
    skip = max(0, int(skip or 0))
    limit = max(1, min(200, int(limit or 50)))
    db = get_db_manager()
    with db.engine.connect() as conn:
        total = conn.execute(select(func.count()).select_from(audit_logs_table)).scalar()
        rows = conn.execute(
            select(audit_logs_table).order_by(audit_logs_table.c.created_at.desc()).limit(limit).offset(skip)
        ).fetchall()
    return {
        "total": total,
        "logs": [{"id": r[0], "operation": r[1], "resource_type": r[2],
                   "resource_id": r[3], "operator": r[4], "created_at": r[5]} for r in rows],
    }
