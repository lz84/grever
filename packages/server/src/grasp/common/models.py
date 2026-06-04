"""
Grasp Skill 数据模型
定义认知相关的输入/输出/存储模型
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class CognitionType(Enum):
    """认知类型"""
    FACT = "fact"  # 事实：客观真理、概念、知识
    PATTERN = "pattern"  # 模式：行为模式、思维模式、解决问题模式
    LESSON = "lesson"  # 经验：从执行结果中总结的经验教训
    META = "meta"  # 元认知：关于认知的认知，如学习如何学习


class CognitionStatus(Enum):
    """认知状态"""
    PUBLISHED = "published"  # 已发布
    PENDING_REVIEW = "pending_review"  # 待审核
    REJECTED = "rejected"  # 已拒绝


@dataclass
class SourceInfo:
    """信息来源"""
    agent_id: str  # 来源 Agent ID
    task_id: str  # 关联任务 ID
    channel: str  # 来源渠道

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SourceInfo':
        return cls(
            agent_id=data.get('agent_id', ''),
            task_id=data.get('task_id', ''),
            channel=data.get('channel', ''),
        )


@dataclass
class CognitionInput:
    """注入认知的输入参数"""
    type: CognitionType  # 认知类型
    content: str  # 认知内容文本
    source: SourceInfo  # 信息来源
    tags: List[str] = field(default_factory=list)  # 标签列表
    confidence: float = 0.8  # 置信度 0-1，默认 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)  # 扩展元数据
    domain: str = ""  # 领域标签，如 "金融"、"项目管理"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CognitionInput':
        source_data = data.get('source', {})
        source = SourceInfo(
            agent_id=source_data.get('agent_id', ''),
            task_id=source_data.get('task_id', ''),
            channel=source_data.get('channel', ''),
        )
        return cls(
            type=CognitionType(data.get('type', 'fact')),
            content=data.get('content', ''),
            source=source,
            tags=data.get('tags', []),
            confidence=data.get('confidence', 0.8),
            metadata=data.get('metadata', {}),
            domain=data.get('domain', ''),
        )


@dataclass
class CognitionUpdate:
    """更新认知的输入参数"""
    content: Optional[str] = None  # 新内容
    tags: Optional[List[str]] = None  # 新标签列表
    confidence: Optional[float] = None  # 新置信度
    metadata: Optional[Dict[str, Any]] = None  # 新元数据


@dataclass
class Cognition:
    """认知实体（存储格式）"""
    cognition_id: str  # 认知 ID
    type: CognitionType  # 认知类型
    content: str  # 认知内容
    tags: List[str] = field(default_factory=list)  # 标签列表
    confidence: float = 0.8  # 置信度
    metadata: Dict[str, Any] = field(default_factory=dict)  # 扩展元数据
    source: SourceInfo = field(default_factory=lambda: SourceInfo(agent_id='', task_id='', channel=''))  # 来源信息
    status: CognitionStatus = CognitionStatus.PENDING_REVIEW  # 状态
    quality_score: float = 0.0  # 质量评分
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = field(default_factory=datetime.now)  # 更新时间
    domain: str = ""  # 领域标签，如 "金融"、"项目管理"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'cognition_id': self.cognition_id,
            'type': self.type.value,
            'content': self.content,
            'tags': self.tags,
            'confidence': self.confidence,
            'metadata': self.metadata,
            'source': {
                'agent_id': self.source.agent_id,
                'task_id': self.source.task_id,
                'channel': self.source.channel,
            },
            'status': self.status.value,
            'quality_score': self.quality_score,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'domain': self.domain,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Cognition':
        source_data = data.get('source', {})
        return cls(
            cognition_id=data['cognition_id'],
            type=CognitionType(data['type']),
            content=data['content'],
            tags=data.get('tags', []),
            confidence=data.get('confidence', 0.8),
            metadata=data.get('metadata', {}),
            source=SourceInfo(
                agent_id=source_data.get('agent_id', ''),
                task_id=source_data.get('task_id', ''),
                channel=source_data.get('channel', ''),
            ),
            status=CognitionStatus(data.get('status', 'pending_review')),
            quality_score=data.get('quality_score', 0.0),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            domain=data.get('domain', ''),
        )


@dataclass
class CognitionItem:
    """认知项（检索结果格式）"""
    cognition_id: str  # 认知 ID
    type: CognitionType  # 认知类型
    content: str  # 认知内容
    tags: List[str] = field(default_factory=list)  # 标签列表
    confidence: float = 0.8  # 置信度
    quality_score: float = 0.0  # 质量评分
    source: SourceInfo = field(default_factory=lambda: SourceInfo(agent_id='', task_id='', channel=''))  # 来源信息
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = field(default_factory=datetime.now)  # 更新时间

    def to_dict(self) -> Dict[str, Any]:
        return {
            'cognition_id': self.cognition_id,
            'type': self.type.value,
            'content': self.content,
            'tags': self.tags,
            'confidence': self.confidence,
            'quality_score': self.quality_score,
            'source': {
                'agent_id': self.source.agent_id,
                'task_id': self.source.task_id,
                'channel': self.source.channel,
            },
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


@dataclass
class InjectResult:
    """注入操作结果"""
    cognition_id: str  # 注入成功的认知 ID
    status: CognitionStatus  # 注入状态
    quality_score: float = 0.0  # 质量评分

    def to_dict(self) -> Dict[str, Any]:
        return {
            'cognition_id': self.cognition_id,
            'status': self.status.value,
            'quality_score': self.quality_score,
        }


@dataclass
class RetrieveResult:
    """检索操作结果"""
    items: List[CognitionItem]  # 匹配的认知项列表
    total: int = 0  # 匹配总数
    has_more: bool = False  # 是否有更多结果

    def to_dict(self) -> Dict[str, Any]:
        return {
            'items': [item.to_dict() for item in self.items],
            'total': self.total,
            'has_more': self.has_more,
        }


@dataclass
class UpdateResult:
    """更新操作结果"""
    cognition_id: str  # 更新的认知 ID
    status: CognitionStatus  # 更新后状态
    quality_score: float = 0.0  # 更新后质量评分
    updated_at: datetime = field(default_factory=datetime.now)  # 更新时间

    def to_dict(self) -> Dict[str, Any]:
        return {
            'cognition_id': self.cognition_id,
            'status': self.status.value,
            'quality_score': self.quality_score,
            'updated_at': self.updated_at.isoformat(),
        }
