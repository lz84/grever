"""
GEP (Genome Evolution Protocol) 协议数据模型

定义 Grever Evo 的三大核心组件：
- Gene（基因）: 可复用技能/策略的标准化描述
- Capsule（记忆体）: 一次完整执行过程的记录
- EvolutionEvent（进化事件）: 进化过程的元数据记录

参考文档: docs/09-系统设计/03-详细设计/进化领域/Evo架构.md §4
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EpigeneticMark:
    """表观遗传标记"""
    mark: str       # 标记类型，如 "platform", "score", "reason"
    value: Any      # 标记值
    timestamp: Optional[str] = None  # ISO 格式时间戳

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"mark": self.mark, "value": self.value}
        if self.timestamp:
            result["timestamp"] = self.timestamp
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EpigeneticMark":
        return cls(
            mark=data.get("mark", ""),
            value=data.get("value"),
            timestamp=data.get("timestamp"),
        )


# ============================================================================
# Gene（基因）
# ============================================================================

@dataclass
class Gene:
    """
    GEP 基因 — 可复用技能/策略的标准化描述

    对应设计文档 §4.1.1 Gene 标准化
    """
    type: str = "gene"
    schema_version: str = "1.0"
    id: str = ""
    category: str = ""               # repair / optimize / innovation / capability / anti_pattern / sequence / pattern
    signals_match: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    strategy: List[Dict[str, Any]] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    validation: List[str] = field(default_factory=list)
    epigenetic_marks: List[EpigeneticMark] = field(default_factory=list)
    asset_id: Optional[str] = None

    # 兼容旧版 ExtractedRule 的字段（内部使用）
    _name: str = ""
    _description: str = ""
    _support_count: int = 0
    _confidence: float = 0.0
    _source_task_ids: List[str] = field(default_factory=list)
    _tags: List[str] = field(default_factory=list)
    _conditions: Dict[str, Any] = field(default_factory=dict)
    _action: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "schema_version": self.schema_version,
            "id": self.id,
            "category": self.category,
            "signals_match": self.signals_match,
            "preconditions": self.preconditions,
            "strategy": self.strategy,
            "constraints": self.constraints,
            "validation": self.validation,
            "epigenetic_marks": [m.to_dict() for m in self.epigenetic_marks],
            "asset_id": self.asset_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Gene":
        marks_data = data.get("epigenetic_marks", [])
        marks = [EpigeneticMark.from_dict(m) if isinstance(m, dict) else m for m in marks_data]
        return cls(
            type=data.get("type", "gene"),
            schema_version=data.get("schema_version", "1.0"),
            id=data.get("id", ""),
            category=data.get("category", ""),
            signals_match=data.get("signals_match", []),
            preconditions=data.get("preconditions", []),
            strategy=data.get("strategy", []),
            constraints=data.get("constraints", {}),
            validation=data.get("validation", []),
            epigenetic_marks=marks,
            asset_id=data.get("asset_id"),
        )

    @property
    def name(self) -> str:
        return self._name or self.id

    @property
    def description(self) -> str:
        return self._description

    @property
    def support_count(self) -> int:
        return self._support_count

    @property
    def confidence(self) -> float:
        return self._confidence

    @property
    def source_task_ids(self) -> List[str]:
        return self._source_task_ids

    @property
    def tags(self) -> List[str]:
        return self._tags

    @property
    def conditions(self) -> Dict[str, Any]:
        return self._conditions

    @property
    def action(self) -> Dict[str, Any]:
        return self._action


# ============================================================================
# Capsule（记忆体）
# ============================================================================

@dataclass
class Capsule:
    """
    GEP 记忆体 — 一次完整执行过程的记录

    对应设计文档 §4.1.2 Capsule 标准化
    """
    type: str = "capsule"
    schema_version: str = "1.0"
    id: str = ""
    trigger: List[str] = field(default_factory=list)
    gene: Optional[str] = None              # 使用的基因 ID
    summary: str = ""
    confidence: float = 0.0
    blast_radius: Dict[str, Any] = field(default_factory=dict)
    outcome: Dict[str, Any] = field(default_factory=dict)   # {"status": "success", "score": 0.88}
    success_streak: int = 0
    content: str = ""
    diff: str = ""
    strategy: List[Dict[str, Any]] = field(default_factory=list)
    a2a: Dict[str, Any] = field(default_factory=dict)       # {"source": "local", "ready_for_hub": false}

    # 兼容旧版 SolidifiedPattern 的字段（内部使用）
    _pattern_id: str = ""
    _pattern_type: str = ""
    _status: str = ""
    _match_conditions: Dict[str, Any] = field(default_factory=dict)
    _template: Dict[str, Any] = field(default_factory=dict)
    _weight_adjustments: Dict[str, float] = field(default_factory=dict)
    _source_rule_ids: List[str] = field(default_factory=list)
    _usage_count: int = 0
    _success_rate: float = 0.0
    _tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "schema_version": self.schema_version,
            "id": self.id,
            "trigger": self.trigger,
            "gene": self.gene,
            "summary": self.summary,
            "confidence": self.confidence,
            "blast_radius": self.blast_radius,
            "outcome": self.outcome,
            "success_streak": self.success_streak,
            "content": self.content,
            "diff": self.diff,
            "strategy": self.strategy,
            "a2a": self.a2a,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Capsule":
        return cls(
            type=data.get("type", "capsule"),
            schema_version=data.get("schema_version", "1.0"),
            id=data.get("id", ""),
            trigger=data.get("trigger", []),
            gene=data.get("gene"),
            summary=data.get("summary", ""),
            confidence=data.get("confidence", 0.0),
            blast_radius=data.get("blast_radius", {}),
            outcome=data.get("outcome", {}),
            success_streak=data.get("success_streak", 0),
            content=data.get("content", ""),
            diff=data.get("diff", ""),
            strategy=data.get("strategy", []),
            a2a=data.get("a2a", {}),
        )

    @property
    def pattern_id(self) -> str:
        return self._pattern_id or self.id

    @property
    def pattern_type(self) -> str:
        return self._pattern_type

    @property
    def status(self) -> str:
        return self._status

    @property
    def match_conditions(self) -> Dict[str, Any]:
        return self._match_conditions

    @property
    def template(self) -> Dict[str, Any]:
        return self._template

    @property
    def weight_adjustments(self) -> Dict[str, float]:
        """从 epigenetic_marks 的 score 标记或内部权重字段提取权重调整"""
        return self._weight_adjustments

    @property
    def gene_id(self) -> Optional[str]:
        """兼容别名：Gene ID"""
        return self.gene

    @property
    def source_rule_ids(self) -> List[str]:
        return self._source_rule_ids

    @property
    def usage_count(self) -> int:
        return self._usage_count

    @property
    def success_rate(self) -> float:
        return self._success_rate

    @property
    def tags(self) -> List[str]:
        return self._tags


# ============================================================================
# EvolutionEvent（进化事件）
# ============================================================================

@dataclass
class EvolutionEvent:
    """
    GEP 进化事件 — 进化过程的元数据记录

    对应设计文档 §4.1.3 EvolutionEvent 标准化
    """
    type: str = "evolution_event"
    schema_version: str = "1.0"
    id: str = ""
    parent: Optional[str] = None
    intent: str = ""
    signals: List[str] = field(default_factory=list)
    genes_used: List[str] = field(default_factory=list)
    mutation_id: str = ""
    blast_radius: Dict[str, Any] = field(default_factory=dict)
    outcome: Dict[str, Any] = field(default_factory=dict)   # {"status": "success", "score": 0.88}
    capsule_id: Optional[str] = None
    validation_report_id: Optional[str] = None
    env_fingerprint: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    # 兼容旧版 WeightUpdate 的字段（内部使用）
    _target_type: str = ""
    _target_id: str = ""
    _field_name: str = ""
    _old_value: float = 0.0
    _new_value: float = 0.0
    _source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "schema_version": self.schema_version,
            "id": self.id,
            "parent": self.parent,
            "intent": self.intent,
            "signals": self.signals,
            "genes_used": self.genes_used,
            "mutation_id": self.mutation_id,
            "blast_radius": self.blast_radius,
            "outcome": self.outcome,
            "capsule_id": self.capsule_id,
            "validation_report_id": self.validation_report_id,
            "env_fingerprint": self.env_fingerprint,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvolutionEvent":
        return cls(
            type=data.get("type", "evolution_event"),
            schema_version=data.get("schema_version", "1.0"),
            id=data.get("id", ""),
            parent=data.get("parent"),
            intent=data.get("intent", ""),
            signals=data.get("signals", []),
            genes_used=data.get("genes_used", []),
            mutation_id=data.get("mutation_id", ""),
            blast_radius=data.get("blast_radius", {}),
            outcome=data.get("outcome", {}),
            capsule_id=data.get("capsule_id"),
            validation_report_id=data.get("validation_report_id"),
            env_fingerprint=data.get("env_fingerprint", {}),
            meta=data.get("meta", {}),
        )

    # 兼容 WeightUpdate 属性
    @property
    def update_id(self) -> str:
        return self.id

    @property
    def parent_id(self) -> Optional[str]:
        """兼容别名：父事件 ID"""
        return self.parent

    @property
    def target_type(self) -> str:
        return self._target_type

    @property
    def target_id(self) -> str:
        return self._target_id

    @property
    def field_name(self) -> str:
        return self._field_name

    @property
    def old_value(self) -> float:
        return self._old_value

    @property
    def new_value(self) -> float:
        return self._new_value

    @property
    def source(self) -> str:
        return self._source

    @property
    def reverted(self) -> bool:
        return self.meta.get("reverted", False)
