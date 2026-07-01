"""Project model — ORM + auto-generated Pydantic schemas"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from typing import Optional
from .base import Base
from .schema_factory import auto_schema

def _generate_project_id():
    return f"proj-{uuid.uuid4().hex[:12]}"

class ProjectStatus(str):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    ARCHIVED = 'archived'
    ON_HOLD = 'on_hold'
    COMPLETED = 'completed'

class ProjectMember(Base):
    __tablename__ = 'project_members'

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey('projects.id'), nullable=False)
    agent_id = Column(String(255), nullable=False)
    role = Column(String(50), default='member')
    joined_at = Column(DateTime, default=datetime.utcnow)

    project = relationship('Project', back_populates='members', foreign_keys=[project_id])

class Project(Base):
    __tablename__ = 'projects'

    id = Column(String(36), primary_key=True, default=_generate_project_id)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    goal_id = Column(String(36), nullable=True)
    status = Column(String(50), default='active')
    priority = Column(String(20), default='medium')
    assignee = Column(String(255), nullable=True)
    due_date = Column(String(50), nullable=True)
    workflow_id = Column(String(36), nullable=True)
    phase_order = Column(Integer, nullable=True)
    matched_scenario_id = Column(String(36), nullable=True)
    created_at = Column(Integer, default=lambda: int(datetime.utcnow().timestamp()))
    updated_at = Column(Integer, default=lambda: int(datetime.utcnow().timestamp()), onupdate=lambda: int(datetime.utcnow().timestamp()))

    # Sprint 53: verifier agent (three-level inheritance)
    verifier_agent_id = Column(String(32), nullable=True)

    # Sprint 78: dependency tracking
    depends_on = Column(Text, nullable=True)  # JSON array of project/task IDs
    # Sprint 79: forward-link for DAG drawing (derived from depends_on)
    next_step = Column(Text, default='[]')  # JSON array of IDs that depend on this project

    # Capability tags: JSON object (business, professional, technical, management)
    capability_tags = Column(Text, nullable=True, default='{}')
    # Sprint 86: 三级上下文文档
    context_md = Column(Text, nullable=True)

    members = relationship('ProjectMember', back_populates='project', lazy='selectin', foreign_keys='ProjectMember.project_id')

    def to_dict(self):
        created = self.created_at
        updated = self.updated_at
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'goal_id': self.goal_id,
            'status': self.status,
            'priority': self.priority,
            'assignee': self.assignee,
            'due_date': self.due_date,
            'created_at': created.isoformat() if isinstance(created, datetime) else datetime.fromtimestamp(created).strftime('%Y-%m-%dT%H:%M:%S') if isinstance(created, (int, float)) else str(created) if created else None,
            'updated_at': updated.isoformat() if isinstance(updated, datetime) else datetime.fromtimestamp(updated).strftime('%Y-%m-%dT%H:%M:%S') if isinstance(updated, (int, float)) else str(updated) if updated else None,
            'member_count': (len(self.members) if self.members else 0) if hasattr(self, 'members') and self.members is not None else 0,
            'workflow_id': self.workflow_id,
            'phase_order': self.phase_order,
            'matched_scenario_id': self.matched_scenario_id,
            'verifier_agent_id': getattr(self, 'verifier_agent_id', None),
            # Sprint 68: 模式字段
            'mode': getattr(self, 'mode', None) or 'engineering',
            # Sprint 78: dependency tracking
            'depends_on': self._parse_depends_on(),
            # Sprint 79: forward-link for DAG drawing
            'next_step': self._parse_next_step(),
            # Capability tags
            'capability_tags': self._parse_capability_tags(),
            # Sprint 86: 三级上下文文档
            'context_md': getattr(self, 'context_md', None),
        }

    def _parse_next_step(self):
        """Parse next_step JSON field"""
        import json
        if not self.next_step:
            return []
        try:
            return json.loads(self.next_step)
        except (json.JSONDecodeError, TypeError):
            return []

    def _parse_depends_on(self):
        """Parse depends_on JSON field"""
        import json
        if not self.depends_on:
            return []
        try:
            return json.loads(self.depends_on)
        except (json.JSONDecodeError, TypeError):
            return []

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
        return f"<Project(id={self.id}, name='{self.name}', status='{self.status}')>"

# Auto-generated Pydantic schemas from ORM columns
from typing import Union, Optional, List, Any
from pydantic import BaseModel, create_model

ProjectCreate, ProjectUpdateBase, ProjectResponseBase = auto_schema(
    Project,
    create_defaults={'status': 'active', 'priority': 'medium'},
)

# Override capability_tags and depends_on for update (accept both str and dict/list)
ProjectUpdate = create_model(
    'ProjectUpdate',
    __base__=ProjectUpdateBase,
    capability_tags=(Optional[Union[str, List[Any], dict]], None),
    depends_on=(Optional[Union[str, List[Any]]], None),
    context_md=(Optional[str], None),  # Sprint 86: 三级上下文文档
)

# Override depends_on to accept both str and list for create, and always return list for response
class ProjectCreateWithArrayDeps(BaseModel):
    """Project create with flexible depends_on (str or list)"""
    name: str
    description: Optional[str] = None
    goal_id: Optional[str] = None
    status: str = 'active'
    priority: str = 'medium'
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    workflow_id: Optional[str] = None
    phase_order: Optional[int] = None
    matched_scenario_id: Optional[str] = None
    verifier_agent_id: Optional[str] = None
    depends_on: Optional[Union[str, List[Any]]] = None

class ProjectResponse(ProjectResponseBase):
    """Project response with depends_on as list"""
    depends_on: Optional[List[Any]] = []
    next_step: Optional[List[Any]] = []
    capability_tags: Optional[dict] = {}
    context_md: Optional[str] = None  # Sprint 86: 三级上下文文档
    # 2026-06-11: created_at/updated_at 已改为 Integer，to_dict 返回 ISO 字符串，Response schema 覆盖为 str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
