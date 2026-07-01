"""Dispute model — ORM + auto-generated Pydantic schemas"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from typing import Optional, List, Any
from .base import Base
from .schema_factory import auto_schema


class DisputeStatus(str):
    """争议状态枚举"""
    OPEN = 'open'
    DISCUSSING = 'discussing'
    RESOLVED = 'resolved'
    ESCALATED = 'escalated'
    CLOSED = 'closed'


class Dispute(Base):
    """Dispute ORM 模型"""
    __tablename__ = 'disputes'

    id = Column(String(36), primary_key=True)
    dispute_type = Column(String(50), nullable=False)  # task, project, goal, etc.
    description = Column(Text, nullable=False)
    involved_agents = Column(Text, nullable=True)  # JSON array of agent IDs
    related_task_id = Column(String(36), ForeignKey('tasks.id'), nullable=True)
    goal_id = Column(String(36), nullable=True)  # 可能关联 goal
    raised_by_agent = Column(String(36), nullable=True)
    status = Column(String(20), default='open')
    resolution = Column(Text, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Discussion log - JSON array of entries
    discussion_log = Column(Text, nullable=True)

    # Sprint 99: deadline tracking
    deadline = Column(DateTime, nullable=True)

    # Relationship
    task = relationship("Task", backref="disputes", foreign_keys=[related_task_id])

    def to_dict(self):
        import json
        involved_agents = []
        if self.involved_agents:
            try:
                involved_agents = json.loads(self.involved_agents) if isinstance(self.involved_agents, str) else self.involved_agents
            except (json.JSONDecodeError, TypeError):
                involved_agents = []

        discussion_log = []
        if self.discussion_log:
            try:
                discussion_log = json.loads(self.discussion_log) if isinstance(self.discussion_log, str) else self.discussion_log
            except (json.JSONDecodeError, TypeError):
                discussion_log = []

        return {
            'id': self.id,
            'dispute_type': self.dispute_type,
            'description': self.description,
            'involved_agents': involved_agents,
            'related_task_id': self.related_task_id,
            'goal_id': self.goal_id,
            'raised_by_agent': self.raised_by_agent,
            'status': self.status,
            'resolution': self.resolution,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'discussion_log': discussion_log,
        }

    def __repr__(self):
        return f"<Dispute(id={self.id}, status='{self.status}')>"


# Auto-generated Pydantic schemas from ORM columns
DisputeCreate, DisputeUpdate, DisputeResponse = auto_schema(
    Dispute,
    create_defaults={
        'status': 'open',
    },
)
