"""Industry Capability Tags ORM models

Sprint 93: 行业能力标签库基础设施
"""
import json
from typing import Optional, List, Any
from datetime import datetime

from sqlalchemy import Column, String, Text, Integer, Index, PrimaryKeyConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

class IndustryCapabilityTag(Base):
    """行业能力标签"""
    __tablename__ = 'industry_capability_tags'

    id = Column(String(36), primary_key=True)
    industry = Column(String(100), nullable=False, index=True)
    tag_name = Column(String(200), nullable=False)
    tag_name_en = Column(String(200), nullable=True)
    description = Column(Text, nullable=False)
    dimension = Column(String(50), nullable=False, index=True)
    level = Column(String(20), nullable=False, default='basic')
    prerequisites = Column(Text, nullable=False, default='[]')
    tools = Column(Text, nullable=False, default='[]')
    examples = Column(Text, nullable=False, default='[]')
    status = Column(String(20), nullable=False, default='active', index=True)
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=True)

    # 版本管理字段
    replaced_by: Mapped[Optional[str]] = mapped_column(Text, ForeignKey('industry_capability_tags.id'), nullable=True)
    version_major: Mapped[int] = mapped_column(Integer, default=1)
    version_minor: Mapped[int] = mapped_column(Integer, default=0)
    version_patch: Mapped[int] = mapped_column(Integer, default=0)
    # replaced_by 直接存储被哪个标签替代（文本 ID，不建 ORM relationship，避免 SQLAlchemy 自引用歧义）
    # 业务层通过查询 replaced_by 字段来追踪替代关系

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'industry': self.industry,
            'tag_name': self.tag_name,
            'tag_name_en': self.tag_name_en,
            'description': self.description,
            'dimension': self.dimension,
            'level': self.level,
            'prerequisites': self._parse_json_field(self.prerequisites),
            'tools': self._parse_json_field(self.tools),
            'examples': self._parse_json_field(self.examples),
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    def _parse_json_field(self, value: str) -> Any:
        """Parse a JSON string field safely."""
        if not value:
            return []
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []

class IndustryPack(Base):
    """行业包元数据"""
    __tablename__ = 'industry_packs'

    id = Column(String(36), primary_key=True)
    name = Column(String(200), nullable=False)
    industry = Column(String(100), nullable=False, index=True)
    version = Column(String(20), nullable=False, default='1.0.0')
    description = Column(Text, nullable=True)
    tags_count = Column(Integer, nullable=False, default=0)
    scenarios_count = Column(Integer, nullable=False, default=0)
    skills_count = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default='draft', index=True)
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=True)

    # 包类型与基础包引用
    pack_type: Mapped[str] = mapped_column(Text, default='standard')
    base_pack_id: Mapped[Optional[str]] = mapped_column(Text, ForeignKey('industry_packs.id'), nullable=True)
    # 自引用 relationship：定制包基于哪个标准包
    base_pack = relationship("IndustryPack", remote_side="IndustryPack.id", foreign_keys=[base_pack_id], lazy="select")

    # Relationship
    contents = relationship('IndustryPackContent', back_populates='pack', cascade='all, delete-orphan')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'industry': self.industry,
            'version': self.version,
            'description': self.description,
            'tags_count': self.tags_count,
            'scenarios_count': self.scenarios_count,
            'skills_count': self.skills_count,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

class IndustryPackContent(Base):
    """行业包内容关联"""
    __tablename__ = 'industry_pack_contents'
    __table_args__ = (
        PrimaryKeyConstraint('pack_id', 'content_type', 'content_id'),
    )

    pack_id = Column(String(36), ForeignKey('industry_packs.id'), primary_key=True)
    content_type = Column(String(50), primary_key=True)  # tag/scenario/skill/knowledge/agent
    content_id = Column(String(100), primary_key=True)

    # Relationship
    pack = relationship('IndustryPack', back_populates='contents')

    def to_dict(self) -> dict:
        return {
            'pack_id': self.pack_id,
            'content_type': self.content_type,
            'content_id': self.content_id,
        }
