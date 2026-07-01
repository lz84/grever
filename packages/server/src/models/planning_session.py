"""Planning Session 模型 — HITL 规划讨论记录

用于记录 Goal 创建时的人机协作规划过程。
"""
import uuid
from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy import Column, String, Text, Integer, Float
from sqlalchemy.orm import relationship
from .base import Base


def _generate_ps_id():
    return f"ps-{uuid.uuid4().hex[:12]}"


class PlanningSession(Base):
    """HITL 规划会话记录"""
    __tablename__ = 'planning_sessions'

    id = Column(String(36), primary_key=True, default=_generate_ps_id)
    goal_id = Column(String(36), nullable=False, index=True)

    # 触发类型
    trigger_type = Column(String(50), nullable=False, default='goal_creation')
    # goal_creation | execution_feedback | user_request

    # 输入
    input_type = Column(String(20), nullable=False, default='text')
    # text | documents | mixed
    input_content = Column(Text, nullable=True)
    document_refs = Column(Text, nullable=True)  # JSON array of file refs

    # 讨论日志
    discussion_log = Column(Text, nullable=True)  # JSON array of {role, content, timestamp}

    # 草稿版本历史
    draft_versions = Column(Text, nullable=True)  # JSON array of {version, plan, status}

    # 状态
    status = Column(String(30), nullable=False, default='drafting')
    # drafting | pending_review | confirmed | abandoned

    # 结果
    confirmed_plan = Column(Text, nullable=True)  # JSON: {projects: [...], assumptions: [...], ...}
    decision_rationale = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(String(50), nullable=True)
    confirmed_at = Column(String(50), nullable=True)

    def to_dict(self):
        import json

        def _parse_json(value):
            if not value:
                return None
            if isinstance(value, (dict, list)):
                return value
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'trigger_type': self.trigger_type,
            'input_type': self.input_type,
            'input_content': self.input_content,
            'document_refs': _parse_json(self.document_refs),
            'discussion_log': _parse_json(self.discussion_log) or [],
            'draft_versions': _parse_json(self.draft_versions) or [],
            'status': self.status,
            'confirmed_plan': _parse_json(self.confirmed_plan),
            'decision_rationale': self.decision_rationale,
            'created_at': self.created_at,
            'confirmed_at': self.confirmed_at,
        }
