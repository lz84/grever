"""Goal Session 模型 — Agent 平台会话记录

记录 Grever 与 Agent 平台（如 OpenClaw）之间的 Coordinator Session 交互。
Grever 不管理会话本身，只记录日志和传递消息。
"""
import uuid
from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy import Column, String, Text
from .base import Base


def _generate_gs_id():
    return f"gs-{uuid.uuid4().hex[:12]}"


class GoalSession(Base):
    """Agent 平台会话记录"""
    __tablename__ = 'goal_sessions'

    id = Column(String(36), primary_key=True, default=_generate_gs_id)
    goal_id = Column(String(36), nullable=False, index=True)

    # Agent 平台返回的 session ID（外部引用）
    session_id = Column(String(100), nullable=True, index=True)

    # 会话类型
    session_type = Column(String(30), nullable=False, default='coordinator')
    # coordinator | decomposition | verification

    # Agent 平台标识
    platform = Column(String(50), nullable=False, default='openclaw')

    # 消息日志
    messages = Column(Text, nullable=True)
    # JSON array of {role: 'outbound'|'inbound', content: str, timestamp: str}

    # 状态
    status = Column(String(20), nullable=False, default='active')
    # active | closed

    # 时间戳
    created_at = Column(String(50), nullable=True)
    closed_at = Column(String(50), nullable=True)

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
            'session_id': self.session_id,
            'session_type': self.session_type,
            'platform': self.platform,
            'messages': _parse_json(self.messages) or [],
            'status': self.status,
            'created_at': self.created_at,
            'closed_at': self.closed_at,
        }
