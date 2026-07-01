"""Industry Capability Tags API Pydantic models

Sprint 93: 行业能力标签库基础设施
Sprint 98 B98-3: PackType 枚举 + 命名空间校验 + 版本计算
"""
import re
from enum import Enum
from typing import Optional, List, Any, Union
from pydantic import BaseModel, Field, field_validator

# ============ Enums ============

class TagDimension(str):
    business = "business"
    professional = "professional"
    technical = "technical"
    management = "management"

    @classmethod
    def values(cls):
        return ["business", "professional", "technical", "management"]

class TagLevel(str):
    basic = "basic"
    intermediate = "intermediate"
    advanced = "advanced"

    @classmethod
    def values(cls):
        return ["basic", "intermediate", "advanced"]

class TagStatus(str):
    active = "active"
    deprecated = "deprecated"
    replaced_by = "replaced_by"

    @classmethod
    def values(cls):
        return ["active", "deprecated", "replaced_by"]

class PackStatus(str):
    draft = "draft"
    published = "published"
    deprecated = "deprecated"

    @classmethod
    def values(cls):
        return ["draft", "published", "deprecated"]

class PackType(str, Enum):
    standard = "standard"
    custom = "custom"

# ============ Namespace Validation ============

# 标准标签格式：行业前缀:能力标识符 (如 chem:msds-parsing)
STANDARD_TAG_PATTERN = re.compile(r'^[a-z]+:[a-z][a-z0-9-]*$')
# 定制标签格式：行业前缀:客户缩写:能力标识符 (如 chem:xxpark:msds-parsing)
CUSTOM_TAG_PATTERN = re.compile(r'^[a-z]+:[a-z]+:[a-z][a-z0-9-]*$')

def validate_tag_id(tag_id: str) -> str:
    """Validate tag ID against namespace rules.

    标准格式: 行业前缀:能力标识符 (如 chem:msds-parsing)
    定制格式: 行业前缀:客户缩写:能力标识符 (如 chem:xxpark:msds-parsing)
    """
    if not STANDARD_TAG_PATTERN.match(tag_id) and not CUSTOM_TAG_PATTERN.match(tag_id):
        raise ValueError(
            f"标签 ID 不符合命名空间规则: {tag_id}。"
            f"标准格式: 行业前缀:能力标识符，"
            f"定制格式: 行业前缀:客户缩写:能力标识符"
        )
    return tag_id

# ============ Version Change Computation ============

def compute_version_change(old_tag: dict, new_tag: dict) -> str:
    """比较标签变更，返回版本级别。

    MAJOR: 标签 ID/维度变更
    MINOR: 描述/名称/工具/示例变更
    PATCH: tools/examples 小更新
    NONE:  无变更
    """
    # 标签 ID 或维度变更 -> MAJOR
    if old_tag.get('id') != new_tag.get('id') or old_tag.get('dimension') != new_tag.get('dimension'):
        return "MAJOR"
    # 描述/名称变更 -> MINOR
    if (old_tag.get('tag_name') != new_tag.get('tag_name') or
            old_tag.get('tag_name_en') != new_tag.get('tag_name_en') or
            old_tag.get('description') != new_tag.get('description')):
        return "MINOR"
    # tools/examples 变更 -> PATCH
    if (old_tag.get('tools') != new_tag.get('tools') or
            old_tag.get('examples') != new_tag.get('examples')):
        return "PATCH"
    return "NONE"

# ============ JSON Field Helper ============

def _parse_json_or_empty(value: Optional[str]) -> List[Any]:
    """Parse a JSON string field, return empty list on failure."""
    import json
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else [result]
    except (json.JSONDecodeError, TypeError):
        return []

# ============ Tag Schemas ============

class IndustryCapabilityTagCreate(BaseModel):
    """创建标签请求"""
    id: str = Field(..., description="标签 ID，格式: 行业前缀:能力标识符")
    industry: str = Field(..., description="行业标识符")
    tag_name: str = Field(..., description="标签名称（中文）")
    tag_name_en: Optional[str] = Field(default=None, description="标签名称（英文）")
    description: str = Field(..., description="能力描述")
    dimension: str = Field(..., description="维度: business/professional/technical/management")
    level: str = Field(default="basic", description="级别: basic/intermediate/advanced")
    prerequisites: Optional[Union[str, List[str]]] = Field(default=None, description="前置标签 ID 列表")
    tools: Optional[Union[str, List[str]]] = Field(default=None, description="关联工具列表")
    examples: Optional[Union[str, List[str]]] = Field(default=None, description="使用示例")
    status: str = Field(default="active", description="状态")

    @field_validator('id')
    @classmethod
    def validate_id_namespace(cls, v: str) -> str:
        return validate_tag_id(v)

class IndustryCapabilityTagUpdate(BaseModel):
    """更新标签请求"""
    tag_name: Optional[str] = None
    tag_name_en: Optional[str] = None
    description: Optional[str] = None
    dimension: Optional[str] = None
    level: Optional[str] = None
    prerequisites: Optional[Union[str, List[str]]] = None
    tools: Optional[Union[str, List[str]]] = None
    examples: Optional[Union[str, List[str]]] = None
    status: Optional[str] = None
    replaced_by: Optional[str] = None
    version_major: Optional[int] = None
    version_minor: Optional[int] = None
    version_patch: Optional[int] = None

class IndustryCapabilityTagResponse(BaseModel):
    """标签响应"""
    id: str
    industry: str
    tag_name: str
    tag_name_en: Optional[str] = None
    description: str
    dimension: str
    level: str
    prerequisites: List[Any] = []
    tools: List[Any] = []
    examples: List[Any] = []
    status: str
    replaced_by: Optional[str] = None
    version_major: int = 1
    version_minor: int = 0
    version_patch: int = 0
    created_at: int
    updated_at: Optional[int] = None

    @classmethod
    def from_orm(cls, tag) -> "IndustryCapabilityTagResponse":
        return cls(
            id=tag.id,
            industry=tag.industry,
            tag_name=tag.tag_name,
            tag_name_en=tag.tag_name_en,
            description=tag.description,
            dimension=tag.dimension,
            level=tag.level,
            prerequisites=_parse_json_or_empty(tag.prerequisites),
            tools=_parse_json_or_empty(tag.tools),
            examples=_parse_json_or_empty(tag.examples),
            status=tag.status,
            replaced_by=getattr(tag, 'replaced_by', None),
            version_major=getattr(tag, 'version_major', 1),
            version_minor=getattr(tag, 'version_minor', 0),
            version_patch=getattr(tag, 'version_patch', 0),
            created_at=tag.created_at,
            updated_at=tag.updated_at,
        )

class TagListResponse(BaseModel):
    """标签列表响应（分页）"""
    items: List[IndustryCapabilityTagResponse]
    total: int
    page: int
    page_size: int

# ============ Pack Schemas ============

class IndustryPackCreate(BaseModel):
    """创建行业包请求"""
    id: str = Field(..., description="行业包 ID")
    name: str = Field(..., description="行业包名称")
    industry: str = Field(..., description="行业标识符")
    version: str = Field(default="1.0.0", description="版本号")
    description: Optional[str] = Field(default=None, description="描述")
    status: str = Field(default="draft", description="状态")
    pack_type: Optional[str] = "standard"
    base_pack_id: Optional[str] = None

class IndustryPackUpdate(BaseModel):
    """更新行业包请求"""
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    tags_count: Optional[int] = None
    scenarios_count: Optional[int] = None
    skills_count: Optional[int] = None
    status: Optional[str] = None
    pack_type: Optional[str] = None
    base_pack_id: Optional[str] = None
    pack_type: Optional[str] = None
    base_pack_id: Optional[str] = None

class IndustryPackResponse(BaseModel):
    """行业包响应"""
    id: str
    name: str
    industry: str
    version: str
    description: Optional[str] = None
    tags_count: int = 0
    scenarios_count: int = 0
    skills_count: int = 0
    status: str
    pack_type: str
    base_pack_id: Optional[str] = None
    created_at: int
    updated_at: Optional[int] = None

    @classmethod
    def from_orm(cls, pack) -> "IndustryPackResponse":
        return cls(
            id=pack.id,
            name=pack.name,
            industry=pack.industry,
            version=pack.version,
            description=pack.description,
            tags_count=pack.tags_count or 0,
            scenarios_count=pack.scenarios_count or 0,
            skills_count=pack.skills_count or 0,
            status=pack.status,
            pack_type=getattr(pack, 'pack_type', 'standard'),
            base_pack_id=getattr(pack, 'base_pack_id', None),
            created_at=pack.created_at,
            updated_at=pack.updated_at,
        )

class PackListResponse(BaseModel):
    """行业包列表响应（分页）"""
    items: List[IndustryPackResponse]
    total: int
    page: int
    page_size: int

# ============ Pack Detail Schema ============

class IndustryPackDetailResponse(IndustryPackResponse):
    """行业包详情响应"""
    pass
