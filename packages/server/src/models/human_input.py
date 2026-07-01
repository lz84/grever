"""Human Input Request model — ORM + auto-generated Pydantic schemas"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from typing import Optional
from .base import Base
from .schema_factory import auto_schema

class HumanInputRequestStatus(str):
    """人类输入请求状态枚举"""
    PENDING = 'pending'
    SUBMITTED = 'submitted'
    REJECTED = 'rejected'

class HumanInputRequest(Base):
    """人类输入请求 ORM 模型"""
    __tablename__ = 'human_input_requests'

    id = Column(String(36), primary_key=True)
    task_id = Column(String(36), ForeignKey('tasks.id'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    input_type = Column(String(50), default='confirmation')  # confirmation, approval, data_entry, selection
    status = Column(String(20), default='pending')
    input_data = Column(Text, nullable=True)  # 存储用户提交的数据
    submitted_by = Column(String(100), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    rejected_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # DB 中实际存在但 model 缺少的字段
    context = Column(Text, nullable=True)  # 请求上下文
    executor_type = Column(String(50), nullable=True)  # 执行者类型

    # Sprint 79: HITL扩展 - 支持 Goal/Project 级
    goal_id = Column(String(36), nullable=True)
    project_id = Column(String(36), nullable=True)
    scenario_ref = Column(Text, nullable=True)
    default_value = Column(Text, nullable=True)
    timeout_action = Column(String(30), nullable=True)  # use_default / skip_project / skip_task / escalate
    timeout_minutes = Column(Integer, nullable=True)
    branches = Column(Text, nullable=True)  # JSON: answer → branch mapping
    response = Column(Text, nullable=True)  # 人类的回答
    responder_id = Column(String(100), nullable=True)  # 回答者 ID

    # Sprint 90: HITL 审计字段
    required_role = Column(String(50), nullable=True)  # 所需角色
    assigned_to = Column(String(100), nullable=True)  # 分配给谁
    approval_reason = Column(Text, nullable=True)  # 审批原因
    before_snapshot = Column(Text, nullable=True)  # 变更前快照

    # Relationship
    task = relationship("Task", back_populates="human_input_requests")

    def to_dict(self):
        import json
        branches_data = None
        if self.branches:
            try:
                branches_data = json.loads(self.branches) if isinstance(self.branches, str) else self.branches
            except (json.JSONDecodeError, TypeError):
                branches_data = None
        return {
            'id': self.id,
            'task_id': self.task_id,
            'goal_id': self.goal_id,
            'project_id': self.project_id,
            'scenario_ref': self.scenario_ref,
            'title': self.title,
            'description': self.description,
            'input_type': self.input_type,
            'status': self.status,
            'input_data': self.input_data,
            'default_value': self.default_value,
            'timeout_action': self.timeout_action,
            'timeout_minutes': self.timeout_minutes,
            'branches': branches_data,
            'response': self.response,
            'responder_id': self.responder_id,
            'submitted_by': self.submitted_by,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'rejected_reason': self.rejected_reason,
            'required_role': getattr(self, 'required_role', None),
            'assigned_to': getattr(self, 'assigned_to', None),
            'approval_reason': getattr(self, 'approval_reason', None),
            'before_snapshot': getattr(self, 'before_snapshot', None),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<HumanInputRequest(id={self.id}, task_id={self.task_id}, status='{self.status}')>"

# Auto-generated Pydantic schemas from ORM columns
HumanInputRequestCreate, HumanInputRequestUpdate, HumanInputRequestResponse = auto_schema(
    HumanInputRequest,
    create_defaults={
        'status': 'pending', 
        'input_type': 'confirmation'
    },
)