"""Artifact 模型 — 成果物 ORM + Pydantic schemas"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from typing import Optional, List
from .base import Base
from .schema_factory import auto_schema


def _generate_artifact_id():
    return f"art-{uuid.uuid4().hex[:12]}"


class Artifact(Base):
    """
    Artifact 成果物表
    
    存储任务或项目输出的成果物（文件、报告等）。
    """
    __tablename__ = 'artifacts'

    id = Column(String(36), primary_key=True, default=_generate_artifact_id)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    storage_path = Column(Text, nullable=True)  # 文件存储路径
    mime_type = Column('type', String(50), nullable=True)  # DB column is 'type'
    size_bytes = Column('size', Integer, nullable=True)  # DB column is 'size'
    task_id = Column(String(36), ForeignKey('tasks.id'), nullable=True, index=True)
    project_id = Column(String(36), ForeignKey('projects.id'), nullable=True, index=True)
    goal_id = Column(String(36), ForeignKey('goals.id'), nullable=True, index=True)
    created_by = Column(String(36), nullable=True)  # 作者
    created_at = Column(DateTime, default=datetime.utcnow)

    def _serialize_dt(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value if value else None
        return value.isoformat()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'storage_path': self.storage_path,
            'mime_type': self.mime_type,
            'size_bytes': self.size_bytes,
            'task_id': self.task_id,
            'project_id': self.project_id,
            'goal_id': self.goal_id,
            'created_by': self.created_by,
            'created_at': self._serialize_dt(self.created_at),
        }

    def __repr__(self):
        return f"<Artifact(id={self.id}, name='{self.name}')>"


# Auto-generated Pydantic schemas
ArtifactCreate, ArtifactUpdate, ArtifactResponse = auto_schema(
    Artifact,
)
