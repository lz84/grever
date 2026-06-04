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

    # Sprint 108: 行业包物理化扩展字段
    format_version: Mapped[Optional[str]] = mapped_column(Text, default='1.0')
    author: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    license: Mapped[Optional[str]] = mapped_column(Text, default='proprietary')
    compatibility_min_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    compatibility_max_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_checksum: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    import_source: Mapped[Optional[str]] = mapped_column(Text, default='created')
    import_source_file: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dependencies: Mapped[Optional[str]] = mapped_column(Text, default='[]')

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
            'pack_type': self.pack_type,
            'base_pack_id': self.base_pack_id,
            'format_version': self.format_version,
            'author': self.author,
            'license': self.license,
            'compatibility_min_version': self.compatibility_min_version,
            'compatibility_max_version': self.compatibility_max_version,
            'source_checksum': self.source_checksum,
            'source_signature': self.source_signature,
            'import_source': self.import_source,
            'import_source_file': self.import_source_file,
            'dependencies': self._parse_json_field(self.dependencies),
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


# ============================================================
# Sprint 108: 行业包物理化 - 新增 ORM 模型
# ============================================================

class IndustryPackVersion(Base):
    """行业包版本历史"""
    __tablename__ = 'industry_pack_versions'

    id = Column(String(36), primary_key=True)
    pack_id = Column(String(36), ForeignKey('industry_packs.id'), nullable=False, index=True)
    version = Column(String(20), nullable=False, index=True)
    action = Column(String(20), nullable=False)  # created / imported / upgraded
    source_file = Column(Text, nullable=True)
    source_checksum = Column(Text, nullable=True)
    stats = Column(Text, nullable=True)  # JSON
    imported_at = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(Integer, nullable=False, default=lambda: int(__import__('time').time()))

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'pack_id': self.pack_id,
            'version': self.version,
            'action': self.action,
            'source_file': self.source_file,
            'source_checksum': self.source_checksum,
            'stats': self._parse_json_field(self.stats),
            'imported_at': self.imported_at,
            'notes': self.notes,
            'created_at': self.created_at,
        }

    @staticmethod
    def _parse_json_field(value):
        if not value:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value


class PromptTemplate(Base):
    """提示词模板"""
    __tablename__ = 'prompt_templates'

    id = Column(String(36), primary_key=True)
    name = Column(String(200), nullable=False)
    scope = Column(String(20), nullable=False, index=True)  # task / project / goal
    template = Column(Text, nullable=False)
    variables = Column(Text, nullable=True)  # JSON array
    tags = Column(Text, nullable=True)  # JSON array
    pack_id = Column(String(36), ForeignKey('industry_packs.id'), nullable=True, index=True)
    created_at = Column(Integer, nullable=False, default=lambda: int(__import__('time').time()))
    updated_at = Column(Integer, nullable=True)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'scope': self.scope,
            'template': self.template,
            'variables': self._parse_json_field(self.variables),
            'tags': self._parse_json_field(self.tags),
            'pack_id': self.pack_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @staticmethod
    def _parse_json_field(value):
        if not value:
            return []
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []


class SOP(Base):
    """标准操作程序 (Standard Operating Procedure)"""
    __tablename__ = 'sops'

    id = Column(String(36), primary_key=True)
    name = Column(String(200), nullable=False)
    industry = Column(String(100), nullable=True, index=True)
    content = Column(Text, nullable=False)
    version = Column(String(20), nullable=True)
    tags = Column(Text, nullable=True)  # JSON array
    related_tasks = Column(Text, nullable=True)  # JSON array
    pack_id = Column(String(36), ForeignKey('industry_packs.id'), nullable=True, index=True)
    created_at = Column(Integer, nullable=False, default=lambda: int(__import__('time').time()))
    updated_at = Column(Integer, nullable=True)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'industry': self.industry,
            'content': self.content,
            'version': self.version,
            'tags': self._parse_json_field(self.tags),
            'related_tasks': self._parse_json_field(self.related_tasks),
            'pack_id': self.pack_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @staticmethod
    def _parse_json_field(value):
        if not value:
            return []
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []


class Checklist(Base):
    """检查清单"""
    __tablename__ = 'checklists'

    id = Column(String(36), primary_key=True)
    name = Column(String(200), nullable=False)
    scope = Column(String(20), nullable=False, index=True)  # pre_task / post_task / pre_project
    items = Column(Text, nullable=False)  # JSON array
    tags = Column(Text, nullable=True)  # JSON array
    related_tasks = Column(Text, nullable=True)  # JSON array
    pack_id = Column(String(36), ForeignKey('industry_packs.id'), nullable=True, index=True)
    created_at = Column(Integer, nullable=False, default=lambda: int(__import__('time').time()))
    updated_at = Column(Integer, nullable=True)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'scope': self.scope,
            'items': self._parse_json_field(self.items),
            'tags': self._parse_json_field(self.tags),
            'related_tasks': self._parse_json_field(self.related_tasks),
            'pack_id': self.pack_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @staticmethod
    def _parse_json_field(value):
        if not value:
            return []
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []


class ReferenceData(Base):
    """参考数据"""
    __tablename__ = 'reference_data'

    id = Column(String(36), primary_key=True)
    name = Column(String(200), nullable=False)
    type = Column(String(20), nullable=False, index=True)  # table / lookup / constants
    data = Column(Text, nullable=False)  # JSON
    tags = Column(Text, nullable=True)  # JSON array
    pack_id = Column(String(36), ForeignKey('industry_packs.id'), nullable=True, index=True)
    created_at = Column(Integer, nullable=False, default=lambda: int(__import__('time').time()))
    updated_at = Column(Integer, nullable=True)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'data': self._parse_json_field(self.data),
            'tags': self._parse_json_field(self.tags),
            'pack_id': self.pack_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @staticmethod
    def _parse_json_field(value):
        if not value:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
