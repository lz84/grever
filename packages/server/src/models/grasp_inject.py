"""
注入管理数据模型

MAK-190: 注入管理模型定义
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, JSON
from pydantic import BaseModel, ConfigDict

from .base import Base

class InjectSource(str):
    """注入来源"""
    TASK = 'task'
    WORKFLOW = 'workflow'
    DISPUTE = 'dispute'

class InjectType(str):
    """注入类型"""
    TASK_RESULT = 'task_result'
    WORKFLOW_RESULT = 'workflow_result'
    DISPUTE_RESULT = 'dispute_result'

class InjectStatus(str):
    """注入状态"""
    SUCCESS = 'success'
    FAILED = 'failed'

# ========== Pydantic 模型 ==========

class InjectRule(BaseModel):
    """注入规则"""
    id: str
    name: str
    trigger_condition: str
    target_kb: str
    enabled: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class UpdateRuleRequest(BaseModel):
    """更新规则请求"""
    enabled: bool

class UpdateRuleResponse(BaseModel):
    """更新规则响应"""
    success: bool = True
    rule: InjectRule

class InjectLogEntry(BaseModel):
    """注入日志条目"""
    id: str
    source: str  # 'task' | 'workflow' | 'dispute'
    type: str  # 'task_result' | 'workflow_result' | 'dispute_result'
    cognition_count: int = 0
    status: str  # 'success' | 'failed'
    error_message: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class InjectStatusResponse(BaseModel):
    """注入状态响应"""
    service_status: str  # 'running' | 'stopped' | 'degraded'
    recent_injections: List[InjectLogEntry] = []

# ========== SQLAlchemy ORM 模型 ==========

def _generate_id():
    return f"inject-{uuid.uuid4().hex[:12]}"

class GraspInjectRule(Base):
    """注入规则表"""
    __tablename__ = 'grasp_inject_rules'

    id = Column(String(36), primary_key=True, default=_generate_id)
    name = Column(String(255), nullable=False)
    trigger_condition = Column(String(500), nullable=False)  # 如 "task.status=done"
    target_kb = Column(String(100), nullable=False)  # 如 "default" 或 "experience"
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'trigger_condition': self.trigger_condition,
            'target_kb': self.target_kb,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

class GraspInjectLog(Base):
    """注入日志表"""
    __tablename__ = 'grasp_inject_logs'

    id = Column(String(36), primary_key=True, default=_generate_id)
    source = Column(String(50), nullable=False, index=True)  # task | workflow | dispute
    type = Column(String(50), nullable=False, index=True)  # task_result | workflow_result | dispute_result
    cognition_count = Column(Integer, default=0)
    status = Column(String(20), nullable=False, default='success')  # success | failed
    error_message = Column(Text, nullable=True)
    extra = Column(JSON, nullable=True)  # renamed from metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'source': self.source,
            'type': self.type,
            'cognition_count': self.cognition_count,
            'status': self.status,
            'error_message': self.error_message,
            'extra': self.extra,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
