"""Goal model — ORM + auto-generated Pydantic schemas"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.types import TypeDecorator, String as SqlString
from sqlalchemy.orm import relationship
from typing import Optional, List
from .base import Base
from .schema_factory import auto_schema

class DateTimeOrString(TypeDecorator):
    """日期时间列，支持空字符串和 NULL"""
    impl = SqlString(50)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is None or value == '':
            return None
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return value

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

class GoalStatus:
    DRAFT = 'draft'
    PLANNED = 'planned'
    IN_PROGRESS = 'in_progress'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'

def _generate_goal_id():
    return f"goal-{uuid.uuid4().hex[:12]}"

class Goal(Base):
    __tablename__ = 'goals'

    id = Column(String(36), primary_key=True, default=_generate_goal_id)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    priority = Column(String(50), default='medium')
    due_date = Column(DateTimeOrString(50))
    status = Column(String(50), default='draft')
    progress = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTimeOrString(50))
    failed_at = Column(DateTimeOrString(50))

    # Sprint 77 P1-1: 删除 project_id（Goal 包含多个 Project，不是属于某个 Project）
    # 原：project_id = Column(String(32), ForeignKey('projects.id'), nullable=True)

    # Tasks 通过 Project 关联，不再直接关联
    # 原：tasks = relationship('Task', back_populates='goal', cascade='all, delete-orphan')

    parent_id = Column(String(32), ForeignKey('goals.id'), nullable=True)
    children = relationship('Goal', back_populates='parent', cascade='all, delete-orphan')
    parent = relationship('Goal', back_populates='children', remote_side=[id])

    # Workspace
    workspace_type = Column(String(10), nullable=True)
    workspace_path = Column(String(500), nullable=True)
    workspace_status = Column(String(20), default='pending')
    workspace_error = Column(Text, nullable=True)
    last_clone_at = Column(DateTime, nullable=True)
    last_pull_at = Column(DateTime, nullable=True)
    last_push_at = Column(DateTime, nullable=True)

    # Sprint 53: verifier agent
    verifier_agent_id = Column(String(32), nullable=True)

    # Sprint 68: 探索模式字段
    mode = Column(String(20), default='normal', nullable=True)
    optimization_target = Column(String(50), nullable=True)
    convergence_threshold = Column(Float, default=0.05, nullable=True)
    max_rounds = Column(Integer, default=10, nullable=True)
    # Sprint 75: 迭代运行状态（与 mode 分离，避免收敛时覆盖用户设置的模式类型）
    run_status = Column(String(20), default='idle', nullable=True)

    # Capability tags: JSON object (business, professional, technical, management)
    capability_tags = Column(Text, nullable=True, default='{}')

    # Scenario matching
    matched_scenario_id = Column(String(36), nullable=True)
    workflow_id = Column(String(36), nullable=True)
    # Sprint 86: 三级上下文文档
    context_md = Column(Text, nullable=True)

    def _serialize_dt(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value if value else None
        return value.isoformat()

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': getattr(self, 'priority', None),
            'due_date': str(getattr(self, 'due_date', None)) if getattr(self, 'due_date', None) else None,
            'status': self.status,
            'progress': getattr(self, 'progress', 0.0),
            'created_at': self._serialize_dt(self.created_at),
            'updated_at': self._serialize_dt(self.updated_at),
            'completed_at': self._serialize_dt(self.completed_at),
            'failed_at': getattr(self, 'failed_at', None),
            # Sprint 77 P1-1: project_id 已删除
            'parent_id': getattr(self, 'parent_id', None),
            'workspace_type': getattr(self, 'workspace_type', None),
            'workspace_path': getattr(self, 'workspace_path', None),
            'workspace_status': getattr(self, 'workspace_status', None),
            'workspace_error': getattr(self, 'workspace_error', None),
            'last_clone_at': self._serialize_dt(self.last_clone_at),
            'last_pull_at': self._serialize_dt(self.last_pull_at),
            'last_push_at': self._serialize_dt(self.last_push_at),
            'verifier_agent_id': getattr(self, 'verifier_agent_id', None),
            'mode': getattr(self, 'mode', None) or 'normal',
            'optimization_target': getattr(self, 'optimization_target', None),
            'convergence_threshold': getattr(self, 'convergence_threshold', None) or 0.05,
            'max_rounds': getattr(self, 'max_rounds', None) or 10,
            # Sprint 75: 迭代运行状态
            'run_status': getattr(self, 'run_status', None) or 'idle',
            # Capability tags
            'capability_tags': self._parse_capability_tags(),
            # Scenario matching
            'matched_scenario_id': getattr(self, 'matched_scenario_id', None),
            'workflow_id': getattr(self, 'workflow_id', None),
            # Sprint 86: 三级上下文文档
            'context_md': getattr(self, 'context_md', None),
        }

    def _parse_capability_tags(self):
        """Parse capability_tags JSON field"""
        import json
        if not self.capability_tags:
            return {}
        try:
            return json.loads(self.capability_tags)
        except (json.JSONDecodeError, TypeError):
            return {}

    def __repr__(self):
        return f"<Goal(id={self.id}, title='{self.title}', status='{self.status}')>"

# Auto-generated Pydantic schemas from ORM columns
from typing import Union as TypingUnion, List as TypingList, Any as TypingAny, Optional
from pydantic import create_model

_GoalCreateBase, _GoalUpdateBase, _GoalResponseBase = auto_schema(
    Goal,
    create_defaults={'status': 'draft', 'priority': 'medium', 'progress': 0.0},
)

# Override capability_tags to accept both str and dict for update
GoalUpdate = create_model(
    'GoalUpdate',
    __base__=_GoalUpdateBase,
    capability_tags=(Optional[TypingUnion[str, TypingList[TypingAny], dict]], None),
    context_md=(Optional[str], None),  # Sprint 86: 三级上下文文档
)

# Add capability_tags as dict for response
GoalResponse = create_model(
    'GoalResponse',
    __base__=_GoalResponseBase,
    capability_tags=(Optional[dict], {}),
    context_md=(Optional[str], None),  # Sprint 86: 三级上下文文档
)

# GoalCreate: keep auto-generated (capability_tags as Optional[str])
GoalCreate = _GoalCreateBase
