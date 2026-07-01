"""GoalIteration 模型 — 迭代记录 ORM + Pydantic schemas"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from typing import Optional, List
from .base import Base
from .schema_factory import auto_schema


def _generate_iteration_id():
    return f"iter-{uuid.uuid4().hex[:12]}"


class GoalIteration(Base):
    """
    GoalIteration 迭代记录表
    
    存储每次方案探索迭代的信息，包括 AI 分析、讨论记录等。
    """
    __tablename__ = 'goal_iterations'

    id = Column(String(36), primary_key=True, default=_generate_iteration_id)
    goal_id = Column(String(36), ForeignKey('goals.id'), nullable=False, index=True)
    iteration_number = Column(Integer, nullable=False)
    solution_id = Column(String(36), nullable=True)  # 关联的方案
    score = Column(Float, nullable=True)  # 方案评分
    status = Column(String(50), default='planned')  # planned/completed/abandoned
    ai_analysis = Column(Text, nullable=True)  # AI 分析和建议
    ai_discussion = Column(Text, nullable=True)  # AI 讨论记录（JSON array）
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
            'iteration_number': self.iteration_number,
            'solution_id': self.solution_id,
            'score': self.score,
            'status': self.status,
            'ai_analysis': self.ai_analysis,
            'ai_discussion': self._parse_json(self.ai_discussion),
            'started_at': self._serialize_dt(self.started_at),
            'completed_at': self._serialize_dt(self.completed_at),
            'created_at': self._serialize_dt(self.created_at),
            'updated_at': self._serialize_dt(self.updated_at),
        }

    def __repr__(self):
        return f"<GoalIteration(id={self.id}, goal_id={self.goal_id}, iteration_number={self.iteration_number})>"


# Auto-generated Pydantic schemas
GoalIterationCreate, GoalIterationUpdate, GoalIterationResponse = auto_schema(
    GoalIteration,
)
