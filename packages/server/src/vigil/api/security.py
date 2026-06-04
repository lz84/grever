"""
安全中心 API 路由

MAK-192: 审计日志和告警 API 补全
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from reins.common.database import get_db
from ..models.security import AuditLog, Alert as AlertModel, AlertLevel, AlertStatus
from ..models.security import (
    AuditLogEntry, AuditLogListResponse,
    Alert, AlertCreate, AlertUpdate, AlertListResponse, AlertCreateResponse
)

router = APIRouter(prefix="/api/v1", tags=["security"])

# ========== 审计日志 API ==========

@router.get("/audit/logs", response_model=AuditLogListResponse)
def list_audit_logs(
    resource_type: Optional[str] = Query(None, description="按资源类型过滤"),
    resource_id: Optional[str] = Query(None, description="按资源 ID 过滤"),
    operation: Optional[str] = Query(None, description="按操作类型过滤"),
    operator: Optional[str] = Query(None, description="按操作者过滤"),
    start_time: Optional[str] = Query(None, description="开始时间 (ISO 8601)"),
    end_time: Optional[str] = Query(None, description="结束时间 (ISO 8601)"),
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(50, ge=1, le=200, description="返回记录数"),
    db: Session = Depends(get_db)
):
    """获取审计日志列表"""
    query = db.query(AuditLog)
    
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.filter(AuditLog.resource_id == resource_id)
    if operation:
        query = query.filter(AuditLog.operation == operation)
    if operator:
        query = query.filter(AuditLog.operator == operator)
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            query = query.filter(AuditLog.created_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            query = query.filter(AuditLog.created_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format")
    
    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    
    return AuditLogListResponse(
        total=total,
        logs=[
            AuditLogEntry(
                id=l.id,
                operation=l.operation,
                resource_type=l.resource_type,
                resource_id=l.resource_id,
                operator=l.operator,
                details=l.details,
                ip_address=l.ip_address,
                user_agent=l.user_agent,
                created_at=l.created_at.isoformat() if l.created_at else None,
            )
            for l in logs
        ]
    )

# ========== 告警 API ==========

@router.get("/alerts", response_model=AlertListResponse)
def list_alerts(
    level: Optional[str] = Query(None, description="按级别过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    category: Optional[str] = Query(None, description="按类别过滤"),
    related_resource_type: Optional[str] = Query(None, description="按相关资源类型过滤"),
    related_resource_id: Optional[str] = Query(None, description="按相关资源 ID 过滤"),
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(50, ge=1, le=200, description="返回记录数"),
    db: Session = Depends(get_db)
):
    """获取告警列表"""
    query = db.query(AlertModel)
    
    if level:
        query = query.filter(AlertModel.level == level)
    if status:
        query = query.filter(AlertModel.status == status)
    if category:
        query = query.filter(AlertModel.category == category)
    if related_resource_type:
        query = query.filter(AlertModel.related_resource_type == related_resource_type)
    if related_resource_id:
        query = query.filter(AlertModel.related_resource_id == related_resource_id)
    
    total = query.count()
    alerts = query.order_by(AlertModel.created_at.desc()).offset(skip).limit(limit).all()
    
    return AlertListResponse(
        total=total,
        alerts=[
            Alert(
                id=a.id,
                title=a.title,
                description=a.description,
                level=a.level,
                category=a.category,
                status=a.status,
                source=a.source,
                related_resource_type=a.related_resource_type,
                related_resource_id=a.related_resource_id,
                resolved_by=a.resolved_by,
                resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
                created_at=a.created_at.isoformat() if a.created_at else None,
                updated_at=a.updated_at.isoformat() if a.updated_at else None,
            )
            for a in alerts
        ]
    )

@router.post("/alerts", response_model=AlertCreateResponse, status_code=status.HTTP_201_CREATED)
def create_alert(alert_data: AlertCreate, db: Session = Depends(get_db)):
    """创建新告警"""
    db_alert = AlertModel(
        title=alert_data.title,
        description=alert_data.description,
        level=alert_data.level,
        category=alert_data.category,
        source=alert_data.source,
        related_resource_type=alert_data.related_resource_type,
        related_resource_id=alert_data.related_resource_id,
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    
    return AlertCreateResponse(
        success=True,
        alert=Alert(
            id=db_alert.id,
            title=db_alert.title,
            description=db_alert.description,
            level=db_alert.level,
            category=db_alert.category,
            status=db_alert.status,
            source=db_alert.source,
            related_resource_type=db_alert.related_resource_type,
            related_resource_id=db_alert.related_resource_id,
            resolved_by=db_alert.resolved_by,
            resolved_at=db_alert.resolved_at.isoformat() if db_alert.resolved_at else None,
            created_at=db_alert.created_at.isoformat() if db_alert.created_at else None,
            updated_at=db_alert.updated_at.isoformat() if db_alert.updated_at else None,
        )
    )

@router.patch("/alerts/{alert_id}", response_model=Alert)
def update_alert_status(
    alert_id: str,
    alert_update: AlertUpdate,
    db: Session = Depends(get_db)
):
    """更新告警状态（确认、解决、关闭）"""
    alert = db.query(AlertModel).filter(AlertModel.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if alert_update.status is not None:
        if alert_update.status not in ['open', 'acknowledged', 'resolved', 'closed']:
            raise HTTPException(status_code=400, detail="Invalid status. Allowed: open, acknowledged, resolved, closed")
        
        # 状态转换验证
        if alert.status == 'closed' and alert_update.status != 'closed':
            raise HTTPException(status_code=400, detail="Cannot change status of a closed alert")
        
        alert.status = alert_update.status
        
        # 如果设置为 resolved 或 closed，记录解决信息
        if alert_update.status in ['resolved', 'closed'] and not alert.resolved_at:
            alert.resolved_at = datetime.utcnow()
    
    if alert_update.resolved_by is not None:
        alert.resolved_by = alert_update.resolved_by
    
    if alert_update.resolved_at is not None:
        try:
            alert.resolved_at = datetime.fromisoformat(alert_update.resolved_at.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid resolved_at format")
    
    db.commit()
    db.refresh(alert)
    
    return Alert(
        id=alert.id,
        title=alert.title,
        description=alert.description,
        level=alert.level,
        category=alert.category,
        status=alert.status,
        source=alert.source,
        related_resource_type=alert.related_resource_type,
        related_resource_id=alert.related_resource_id,
        resolved_by=alert.resolved_by,
        resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
        created_at=alert.created_at.isoformat() if alert.created_at else None,
        updated_at=alert.updated_at.isoformat() if alert.updated_at else None,
    )

@router.get("/alerts/{alert_id}", response_model=Alert)
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    """获取单个告警详情"""
    from sqlalchemy import text
    try:
        alert = db.query(AlertModel).filter(AlertModel.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return Alert(
            id=alert.id,
            title=alert.title,
            description=alert.description,
            level=alert.level,
            category=alert.category,
            status=alert.status,
            source=alert.source,
            related_resource_type=alert.related_resource_type,
            related_resource_id=alert.related_resource_id,
            resolved_by=alert.resolved_by,
            resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
            created_at=alert.created_at.isoformat() if alert.created_at else None,
            updated_at=alert.updated_at.isoformat() if alert.updated_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert: {str(e)}")

@router.delete("/alerts/{alert_id}", status_code=204)
def delete_alert(alert_id: str, db: Session = Depends(get_db)):
    """删除告警"""
    from sqlalchemy import text
    try:
        alert = db.query(AlertModel).filter(AlertModel.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        db.delete(alert)
        db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete alert: {str(e)}")
