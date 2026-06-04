"""Solution 模型 — 方案库 ORM + Pydantic schemas"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from typing import Optional, List, Dict, Any
from .base import Base
from .schema_factory import auto_schema

class SolutionStatus:
    """方案状态枚举"""
    OPTIMAL = 'optimal'           # 最优方案
    COMPLIANT = 'compliant'       # 符合约束
    NON_COMPLIANT = 'non_compliant'  # 不符合约束
    REJECTED = 'rejected'         # 被拒绝

def _generate_solution_id():
    return f"sol-{uuid.uuid4().hex[:12]}"

class Solution(Base):
    __tablename__ = 'solutions'

    id = Column(String(36), primary_key=True, default=_generate_solution_id)
    goal_id = Column(String(36), ForeignKey('goals.id'), nullable=True)
    round = Column(Integer, default=1)
    name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)  # optimal/compliant/non_compliant/rejected
    parameters = Column(Text, nullable=True)  # JSON: 关键参数
    dimensions = Column(Text, nullable=True)  # JSON: 多维度评估数据
    score = Column(Float, nullable=True)
    is_optimal = Column(Boolean, default=False)
    project_ids = Column(Text, nullable=True)  # JSON array
    task_ids = Column(Text, nullable=True)  # JSON array
    constraints = Column(Text, nullable=True)  # JSON: 本轮约束
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
            'round': self.round,
            'name': self.name,
            'status': self.status,
            'parameters': self._parse_json(self.parameters),
            'dimensions': self._parse_json(self.dimensions),
            'score': self.score,
            'is_optimal': self.is_optimal,
            'project_ids': self._parse_json(self.project_ids),
            'task_ids': self._parse_json(self.task_ids),
            'constraints': self._parse_json(self.constraints),
            'created_at': self._serialize_dt(self.created_at),
            'updated_at': self._serialize_dt(self.updated_at),
        }

    def __repr__(self):
        return f"<Solution(id={self.id}, name='{self.name}', score={self.score})>"

# Auto-generated Pydantic schemas
SolutionCreate, SolutionUpdate, SolutionResponse = auto_schema(
    Solution,
    create_defaults={'round': 1, 'is_optimal': False},
)
