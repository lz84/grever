"""Pydantic schemas for Grasp API"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class CognitionTypeEnum(str, Enum):
    """认知类型 — 与业务概念一致（第二章 2.1 五类知识）"""
    WHAT = "what"           # 事实性知识
    HOW = "how"             # 过程性知识
    WHY = "why"             # 因果性知识
    LESSONS = "lessons"     # 经验教训
    META = "meta"           # 元知识


class CognitionInjectRequest(BaseModel):
    type: CognitionTypeEnum = CognitionTypeEnum.WHAT
    content: str = Field(..., min_length=1, max_length=10000, description="认知内容")
    tags: List[str] = Field(default_factory=list, description="业务标签")
    confidence: float = Field(default=0.8, ge=0, le=1, description="置信度 0-1")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    domain: Optional[str] = Field(default=None, description="领域（用于后端路由）")


class CognitionRetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, description="查询文本")
    mode: str = Field(default="local", description="检索模式: local/global/drift/basic")
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0, description="分页偏移")
    type: Optional[List[CognitionTypeEnum]] = None
    tags: Optional[List[str]] = None
    min_confidence: float = Field(default=0.0, ge=0, le=1)
    domain: Optional[str] = Field(default=None, description="领域（用于路由对称）")


class CognitionItemResponse(BaseModel):
    cognition_id: str
    type: str
    content: str
    tags: List[str]
    confidence: float
    quality_score: float
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CognitionRetrieveResponse(BaseModel):
    items: List[CognitionItemResponse]
    total: int
    has_more: bool


class CognitionInjectResponse(BaseModel):
    cognition_id: str
    status: str
    quality_score: float
    is_duplicate: bool = False


class CognitionUpdateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BackendStatusResponse(BaseModel):
    name: str
    available: bool
    index_size: Optional[int] = None
    backend_version: Optional[str] = None


class SwitchBackendRequest(BaseModel):
    backend_name: str = Field(..., description="目标后端名称")
