"""
GrASP Facade + Adapter 数据模型
用于门面层与适配层之间的数据交换
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class CognitionInput:
    """注入认知的输入参数（适配层接口）"""
    content: str
    type: str = "what"  # what/how/why/lessons/meta
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)
    domain: Optional[str] = None

    @property
    def cognition_id(self) -> Optional[str]:
        """兼容旧代码：CognitionInput 不持有 cognition_id"""
        return getattr(self, '_cognition_id', None)

    @cognition_id.setter
    def cognition_id(self, value: str):
        self._cognition_id = value


@dataclass
class CognitionItem:
    """认知项（检索结果中的单条）"""
    cognition_id: str
    type: str
    content: str
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.8
    quality_score: float = 0.0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cognition_id": self.cognition_id,
            "type": self.type,
            "content": self.content,
            "tags": self.tags,
            "confidence": self.confidence,
            "quality_score": self.quality_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class InjectResult:
    """注入操作结果"""
    cognition_id: str
    backend: str = ""
    quality_score: float = 0.0
    is_duplicate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cognition_id": self.cognition_id,
            "backend": self.backend,
            "quality_score": self.quality_score,
            "is_duplicate": self.is_duplicate,
        }


@dataclass
class RetrieveResult:
    """检索操作结果"""
    items: List[CognitionItem] = field(default_factory=list)
    total: int = 0
    has_more: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "total": self.total,
            "has_more": self.has_more,
        }


@dataclass
class UpdateResult:
    """更新操作结果"""
    cognition_id: str
    quality_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cognition_id": self.cognition_id,
            "quality_score": self.quality_score,
        }
