"""IterationConstraint 模型 — 迭代约束记录 ORM + Pydantic schemas"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from typing import Optional
from .base import Base
from .schema_factory import auto_schema

def _generate_constraint_id():
    return f"ic-{uuid.uuid4().hex[:12]}"

class IterationConstraint(Base):
    __tablename__ = 'iteration_constraints'

    id = Column(String(36), primary_key=True, default=_generate_constraint_id)
    goal_id = Column(String(36), ForeignKey('goals.id'), nullable=True)
    round = Column(Integer, nullable=True)
    constraints = Column(Text, nullable=True)  # JSON: 约束配置
    reason = Column(Text, nullable=True)  # 调整原因
    created_by = Column(String(36), nullable=True)  # 创建者（human/system）
    created_at = Column(DateTime, default=datetime.utcnow)

    def _serialize_dt(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value if value else None
        return value.isoformat()

    def _parse_json(self, value):
        """解析 JSON 字符串"""
        import json
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value

    def to_dict(self):
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'round': self.round,
            'constraints': self._parse_json(self.constraints),
            'reason': self.reason,
            'created_by': self.created_by,
            'created_at': self._serialize_dt(self.created_at),
        }

    def __repr__(self):
        return f"<IterationConstraint(id={self.id}, goal_id={self.goal_id}, round={self.round})>"

# Auto-generated Pydantic schemas
IterationConstraintCreate, IterationConstraintUpdate, IterationConstraintResponse = auto_schema(
    IterationConstraint,
)
