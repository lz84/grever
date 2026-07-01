"""ExecutionLog model - 执行日志 ORM"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, ForeignKey
from .base import Base
from .schema_factory import auto_schema


def _generate_log_id():
    return f"elog-{uuid.uuid4().hex[:12]}"


def _get_execution_log_metadata(self) -> dict:
    """Compat property: maps meta_data (ORM) → metadata (API)."""
    import json
    if self.meta_data:
        try:
            return json.loads(self.meta_data)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


class ExecutionLog(Base):
    """执行日志表"""
    __tablename__ = 'execution_logs'

    id = Column(String(36), primary_key=True, default=_generate_log_id)
    task_id = Column(String(32), ForeignKey('tasks.id'), nullable=False, index=True)
    agent_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False)
    input = Column(Text, nullable=True)
    output = Column(Text, nullable=True)
    status = Column(String(50), nullable=False)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    meta_data = Column('metadata', Text, nullable=True)  # DB column name is 'metadata'


# Define metadata property AFTER class definition to avoid SQLAlchemy declarative capturing it
ExecutionLog.metadata = property(_get_execution_log_metadata)


ExecutionLogCreate, ExecutionLogUpdate, ExecutionLogResponse = auto_schema(
    ExecutionLog,
    create_exclude={'id', 'created_at', 'updated_at'},
    update_exclude={'id'},
)
