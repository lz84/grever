"""Additional ORM models for tables not yet covered.

Tables: genes, evolution_events, capsules, a2a_messages,
        trust_evaluations, roles, scenario_projects, scenario_tasks,
        scenarios, task_labels, task_relations, attachments,
        attachment_links
"""
import json
from datetime import datetime
from typing import Optional, List, Any

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship

from .base import Base


# ============================================================================
# genes — Evo 基因表
# ============================================================================

class Gene(Base):
    __tablename__ = 'genes'

    id = Column(String(36), primary_key=True)
    schema_version = Column(String(20), nullable=False, default='1.0')
    category = Column(String(50), nullable=False, index=True)
    signals_match = Column(Text, nullable=True)  # JSON
    preconditions = Column(Text, nullable=True)  # JSON
    strategy = Column(Text, nullable=True)  # JSON
    constraints = Column(Text, nullable=True)  # JSON
    validation = Column(Text, nullable=True)  # JSON
    epigenetic_marks = Column(Text, nullable=True)  # JSON
    asset_id = Column(String(36), nullable=True, index=True)
    created_at = Column(String(50), nullable=True)
    updated_at = Column(String(50), nullable=True)

    def _parse_json(self, value):
        if not value:
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
            'schema_version': self.schema_version,
            'category': self.category,
            'signals_match': self._parse_json(self.signals_match),
            'preconditions': self._parse_json(self.preconditions),
            'strategy': self._parse_json(self.strategy),
            'constraints': self._parse_json(self.constraints),
            'validation': self._parse_json(self.validation),
            'epigenetic_marks': self._parse_json(self.epigenetic_marks),
            'asset_id': self.asset_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


# ============================================================================
# evolution_events — Evo 进化事件表
# ============================================================================

class EvolutionEvent(Base):
    __tablename__ = 'evolution_events'

    id = Column(String(36), primary_key=True)
    event_type = Column(String(50), nullable=False, index=True)
    capsule_id = Column(String(36), nullable=True, index=True)
    gene_id = Column(String(36), nullable=True, index=True)
    meta = Column(Text, nullable=True)  # JSON
    outcome = Column(Text, nullable=True)  # JSON
    score = Column(Float, nullable=True)
    created_at = Column(String(50), nullable=True)

    def _parse_json(self, value):
        if not value:
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
            'event_type': self.event_type,
            'capsule_id': self.capsule_id,
            'gene_id': self.gene_id,
            'meta': self._parse_json(self.meta),
            'outcome': self._parse_json(self.outcome),
            'score': self.score,
            'created_at': self.created_at,
        }


# ============================================================================
# capsules — Evo 胶囊表
# ============================================================================

class Capsule(Base):
    __tablename__ = 'capsules'

    id = Column(String(36), primary_key=True)
    schema_version = Column(Integer, nullable=False, default=1)
    trigger = Column(Text, nullable=True)  # JSON
    gene_id = Column(String(36), nullable=True, index=True)
    summary = Column(String(2000), nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    blast_radius = Column(Text, nullable=True)  # JSON
    outcome = Column(Text, nullable=True)  # JSON
    success_streak = Column(Integer, nullable=False, default=0)
    content = Column(String(5000), nullable=True)
    diff = Column(String(5000), nullable=True)
    strategy = Column(Text, nullable=True)  # JSON
    created_at = Column(String(50), nullable=True)

    def _parse_json(self, value):
        if not value:
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
            'schema_version': self.schema_version,
            'trigger': self._parse_json(self.trigger),
            'gene_id': self.gene_id,
            'summary': self.summary,
            'confidence': self.confidence,
            'blast_radius': self._parse_json(self.blast_radius),
            'outcome': self._parse_json(self.outcome),
            'success_streak': self.success_streak,
            'content': self.content,
            'diff': self.diff,
            'strategy': self._parse_json(self.strategy),
            'created_at': self.created_at,
        }


# ============================================================================
# a2a_messages — Agent-to-Agent 消息表
# ============================================================================

class A2AMessage(Base):
    __tablename__ = 'a2a_messages'

    id = Column(String(36), primary_key=True)
    broadcast_id = Column(String(36), nullable=True, index=True)
    source_agent_id = Column(String(36), nullable=False, index=True)
    target_agent_id = Column(String(36), nullable=False, index=True)
    message = Column(String(5000), nullable=False)
    channel = Column(String(50), nullable=False, default='default')
    priority = Column(String(20), nullable=False, default='normal')
    status = Column(String(20), nullable=False, default='pending', index=True)
    msg_metadata = Column('metadata', Text, nullable=True)  # JSON, DB column name is 'metadata'
    requires_ack = Column(Boolean, default=False)
    ack_status = Column(String(20), nullable=True)
    ack_response = Column(String(5000), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)
    ack_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'broadcast_id': self.broadcast_id,
            'source_agent_id': self.source_agent_id,
            'target_agent_id': self.target_agent_id,
            'message': self.message,
            'channel': self.channel,
            'priority': self.priority,
            'status': self.status,
            'metadata': self._parse_json(self.msg_metadata),
            'requires_ack': self.requires_ack,
            'ack_status': self.ack_status,
            'ack_response': self.ack_response,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at) if self.created_at else None,
            'delivered_at': self.delivered_at.isoformat() if isinstance(self.delivered_at, datetime) else str(self.delivered_at) if self.delivered_at else None,
            'ack_at': self.ack_at.isoformat() if isinstance(self.ack_at, datetime) else str(self.ack_at) if self.ack_at else None,
        }

    @staticmethod
    def _parse_json(value):
        if not value:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value


# ============================================================================
# trust_evaluations — 信任评估表
# ============================================================================

class TrustEvaluation(Base):
    __tablename__ = 'trust_evaluations'

    id = Column(String(36), primary_key=True)
    agent_id = Column(String(36), nullable=False, index=True)
    score = Column(Float, nullable=False)
    level = Column(String(20), nullable=False)
    reason = Column(String(1000), nullable=True)
    category = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'score': self.score,
            'level': self.level,
            'reason': self.reason,
            'category': self.category,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at) if self.created_at else None,
        }


# ============================================================================
# roles — RBAC 角色表
# ============================================================================

class Role(Base):
    __tablename__ = 'roles'

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    permissions = Column(Text, nullable=True)  # JSON
    level = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default='active', index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def _parse_json(self, value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'permissions': self._parse_json(self.permissions),
            'level': self.level,
            'status': self.status,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at) if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at) if self.updated_at else None,
        }


# ============================================================================
# task_labels — 任务标签表
# ============================================================================

class TaskLabel(Base):
    __tablename__ = 'task_labels'

    id = Column(String(36), primary_key=True)
    task_id = Column(String(36), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    color = Column(String(20), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'name': self.name,
            'color': self.color,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at) if self.created_at else None,
        }


# ============================================================================
# task_relations — 任务关系表 (many-to-many join)
# ============================================================================

class TaskRelation(Base):
    __tablename__ = 'task_relations'

    id = Column(String(36), primary_key=True)
    parent_task_id = Column(String(36), nullable=False, index=True)
    child_task_id = Column(String(36), nullable=False, index=True)
    relation_type = Column(String(50), nullable=True, default='depends_on')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'parent_task_id': self.parent_task_id,
            'child_task_id': self.child_task_id,
            'relation_type': self.relation_type,
        }


# ============================================================================
# attachments — 附件表
# ============================================================================

class Attachment(Base):
    __tablename__ = 'attachments'

    id = Column(String(36), primary_key=True)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    sha256_hash = Column(String(64), nullable=True, index=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at) if self.created_at else None,
        }


# ============================================================================
# attachment_links — 附件关联表 (many-to-many join)
# ============================================================================

class AttachmentLink(Base):
    __tablename__ = 'attachment_links'

    id = Column(String(36), primary_key=True)
    attachment_id = Column(String(36), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)  # 'task', 'project', 'goal', etc.
    entity_id = Column(String(36), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'attachment_id': self.attachment_id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
        }
