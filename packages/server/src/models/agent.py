"""Agent model — ORM + auto-generated Pydantic schemas"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from typing import Optional
from .base import Base
from .schema_factory import auto_schema


class Agent(Base):
    __tablename__ = 'agents'

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    capability_tags = Column(Text, nullable=False)  # JSON object: {business:[], professional:[], technical:[], management:[]}
    tag_weights = relationship('AgentTagWeight', back_populates='agent', lazy='select', cascade='all, delete-orphan')
    status = Column(String(20), nullable=False)
    address = Column(String(500), nullable=True)
    meta_data = Column('metadata', Text, nullable=True)  # DB column is 'metadata', Python attr is 'meta_data' to avoid SQLAlchemy reserved name
    load = Column(Integer, nullable=False, default=0)
    current_tasks = Column(Integer, nullable=False, default=0)
    registered_at = Column(DateTime, nullable=False)
    last_heartbeat = Column(DateTime, nullable=False)
    trigger_mode = Column(String(20), nullable=False, default='sse')
    poll_interval_seconds = Column(Integer, nullable=False, default=10)
    max_concurrent_tasks = Column(Integer, nullable=False, default=5)
    load_threshold = Column(Integer, nullable=False, default=80)
    recovery_threshold = Column(Integer, nullable=False, default=50)
    updated_at = Column(DateTime, nullable=True)
    model_name = Column(String(255), nullable=True)
    health_status = Column(String(20), nullable=True, default='online')
    last_status_change = Column(DateTime, nullable=True)
    consecutive_offline_count = Column(Integer, nullable=True, default=0)
    max_offline_before_deactivate = Column(Integer, nullable=True, default=5)
    platform_type = Column(String(32), nullable=False, default='openclaw')
    agent_code = Column(String(32), nullable=True)  # OpenClaw agent code (replaces hardcoded UUID mapping)

    # Relationship to agents_config (config per platform)
    config_relationship = relationship(
        'AgentConfig',  # Will define below
        back_populates='agent',
        uselist=False,
        lazy='joined',
        cascade='all, delete-orphan'
    )

    @property
    def platform_config(self) -> dict:
        """Return platform config dict from agents_config table."""
        if self.config_relationship:
            import json
            try:
                return json.loads(self.config_relationship.config_json or '{}')
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}


def _get_agent_metadata(self) -> dict:
    """Compat property: maps meta_data (ORM) → metadata (API)."""
    import json
    if self.meta_data:
        try:
            return json.loads(self.meta_data)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


# Define metadata property AFTER class definition to avoid SQLAlchemy declarative capturing it
Agent.metadata = property(_get_agent_metadata)


AgentSchema, AgentCreate, AgentUpdate = auto_schema(Agent)

# 补充 platform 相关字段（auto_schema 不暴露 ORM property，手动补）
from pydantic import Field
AgentCreate.model_fields['platform_type'] = Field(default='openclaw', description="智能体平台类型")
AgentCreate.model_fields['platform_config'] = Field(default=None, description="平台特有配置字典")
AgentSchema.model_fields['platform_type'] = Field(default='openclaw')
AgentSchema.model_fields['platform_config'] = Field(default=None)


class AgentConfig(Base):
    """Per-platform config for agents — separate table for multi-platform support."""
    __tablename__ = 'agents_config'

    agent_id = Column(String(32), ForeignKey('agents.id', ondelete='CASCADE'), primary_key=True)
    platform_type = Column(String(32), nullable=False, default='openclaw')
    config_json = Column(Text, nullable=False, default='{}')
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    agent = relationship('Agent', back_populates='config_relationship')


class AgentTagWeight(Base):
    """Agent tag weight storage — separate table for multi-dimensional weights."""
    __tablename__ = 'agent_tag_weights'

    agent_id = Column(String(32), ForeignKey('agents.id'), primary_key=True)
    tag = Column(String(100), primary_key=True)
    weight = Column(Float, nullable=False, default=1.0)
    last_observed = Column(DateTime, default=datetime.utcnow)

    agent = relationship('Agent', back_populates='tag_weights')

    def to_dict(self):
        return {
            'agent_id': self.agent_id,
            'tag': self.tag,
            'weight': self.weight,
            'last_observed': self.last_observed.isoformat() if self.last_observed else None,
        }

    def __repr__(self):
        return f"<AgentTagWeight(agent_id={self.agent_id}, tag='{self.tag}', weight={self.weight})>"
