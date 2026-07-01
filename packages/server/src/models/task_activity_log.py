"""TaskActivityLog model - 任务活动日志 ORM"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from .base import Base
from .schema_factory import auto_schema


def _generate_activity_id():
    return f"act-{uuid.uuid4().hex[:12]}"


class TaskActivityLog(Base):
    """任务活动日志表"""
    __tablename__ = 'task_activity_log'

    id = Column(String(36), primary_key=True, default=_generate_activity_id)
    task_id = Column(String(32), ForeignKey('tasks.id'), nullable=False, index=True)
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    reason = Column(Text, nullable=True)
    actor = Column(String(36), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


TaskActivityLogCreate, TaskActivityLogUpdate, TaskActivityLogResponse = auto_schema(
    TaskActivityLog,
    create_exclude={'id', 'created_at', 'updated_at'},
    update_exclude={'id'},
)
