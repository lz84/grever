"""TaskComment 模型 — 任务评论 ORM + Pydantic schemas"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from typing import Optional, List, Dict, Any
from .base import Base
from .schema_factory import auto_schema


def _generate_comment_id():
    return f"cmt-{uuid.uuid4().hex[:8]}"


class TaskComment(Base):
    """
    TaskComment 任务评论表
    
    存储任务相关的各种评论，包括验证结果、重调度记录等。
    """
    __tablename__ = 'task_comments'

    id = Column(String(36), primary_key=True, default=_generate_comment_id)
    task_id = Column(String(32), ForeignKey('tasks.id'), nullable=False, index=True)
    author = Column(String(36), nullable=False)  # 作者（agent ID 或 "verifier"）
    author_role = Column(String(50), nullable=False)  # verifier/system/human
    type = Column(String(50), nullable=False)  # verification_result/redispatch
    content = Column(Text, nullable=False)
    meta_data = Column('metadata', Text, nullable=True)  # DB column name is 'metadata' (remote server doesn't have meta_data)
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
            'task_id': self.task_id,
            'author': self.author,
            'author_role': self.author_role,
            'type': self.type,
            'content': self.content,
            'metadata': self._parse_json(self.meta_data),
            'created_at': self._serialize_dt(self.created_at),
        }

    def __repr__(self):
        return f"<TaskComment(id={self.id}, task_id={self.task_id}, type={self.type})>"


# Auto-generated Pydantic schemas
TaskCommentCreate, TaskCommentUpdate, TaskCommentResponse = auto_schema(
    TaskComment,
)
