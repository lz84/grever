"""
安全中心数据模型

MAK-192: 审计日志和告警模型定义
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON
from pydantic import BaseModel, ConfigDict

from .base import Base

class AlertLevel(str):
    """告警级别"""
    CRITICAL = 'critical'
    WARNING = 'warning'
    INFO = 'info'

class AlertStatus(str):
    """告警状态"""
    OPEN = 'open'
    ACKNOWLEDGED = 'acknowledged'
    RESOLVED = 'resolved'
    CLOSED = 'closed'

class AuditOperation(str):
    """审计操作类型"""
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'
    ACCESS = 'access'

# ========== Pydantic 模型 ==========

class AuditLogEntry(BaseModel):
    """审计日志条目"""
    id: str
    operation: str
    resource_type: str
    resource_id: str
    operator: str
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class Alert(BaseModel):
    """告警"""
    id: str
    title: str
    description: Optional[str] = None
    level: str
    category: str
    status: str
    source: Optional[str] = None
    related_resource_type: Optional[str] = None
    related_resource_id: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class AlertCreate(BaseModel):
    """创建告警请求"""
    title: str
    description: Optional[str] = None
    level: str = 'warning'
    category: str
    source: Optional[str] = None
    related_resource_type: Optional[str] = None
    related_resource_id: Optional[str] = None

class AlertUpdate(BaseModel):
    """更新告警请求"""
    status: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None

class AlertListResponse(BaseModel):
    """告警列表响应"""
    total: int
    alerts: list[Alert]

class AuditLogListResponse(BaseModel):
    """审计日志列表响应"""
    total: int
    logs: list[AuditLogEntry]

class AlertCreateResponse(BaseModel):
    """创建告警响应"""
    success: bool = True
    alert: Alert

# ========== SQLAlchemy ORM 模型 ==========

def _generate_id(prefix: str = 'audit') -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"

class AuditLog(Base):
    """审计日志表"""
    __tablename__ = 'audit_logs'

    id = Column(String(36), primary_key=True, default=lambda: _generate_id('audit'))
    operation = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(36), nullable=False, index=True)
    operator = Column(String(32), nullable=False, index=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'operation': self.operation,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'operator': self.operator,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class AlertModel(Base):
    """告警表"""
    __tablename__ = 'alerts'

    id = Column(String(36), primary_key=True, default=lambda: _generate_id('alert'))
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    level = Column(String(20), nullable=False, default='warning', index=True)
    category = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default='open', index=True)
    source = Column(String(100), nullable=True)
    related_resource_type = Column(String(50), nullable=True, index=True)
    related_resource_id = Column(String(36), nullable=True, index=True)
    resolved_by = Column(String(32), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'level': self.level,
            'category': self.category,
            'status': self.status,
            'source': self.source,
            'related_resource_type': self.related_resource_type,
            'related_resource_id': self.related_resource_id,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
