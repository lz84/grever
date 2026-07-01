"""Grasp 综合研判 — 数据模型"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional

from .plans import Plan


class ApplicabilityLevel(Enum):
    """适用性等级"""
    HIGHLY_APPLICABLE = "高度适用"
    PARTIALLY_APPLICABLE = "部分适用"
    LOW_APPLICABILITY = "低适用"
    NOT_APPLICABLE = "不适用"


class ConflictType(Enum):
    """冲突类型"""
    RESOURCE_CONFLICT = "资源冲突"
    TIME_CONFLICT = "时间冲突"
    PRIORITY_CONFLICT = "优先级冲突"
    LOGICAL_CONFLICT = "逻辑冲突"


class StepPriority(Enum):
    """步骤优先级"""
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


@dataclass
class TaskStep:
    """任务步骤"""
    step_id: str
    name: str
    description: str
    priority: str = "P1"
    source_plan_id: str = ""
    source_plan_name: str = ""
    estimated_duration: str = ""
    dependencies: List[str] = field(default_factory=list)
    required_resources: Dict[str, Any] = field(default_factory=dict)
    assigned_agents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlanApplicability:
    """预案适用性分析结果"""
    plan: Plan
    applicability_level: ApplicabilityLevel
    applicability_score: float
    applicable_tasks: List[Dict[str, Any]] = field(default_factory=list)
    inapplicable_tasks: List[Dict[str, Any]] = field(default_factory=list)
    adaptation_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'plan': self.plan.to_dict(),
            'applicability_level': self.applicability_level.value,
            'applicability_score': round(self.applicability_score, 4),
            'applicable_tasks': self.applicable_tasks,
            'inapplicable_tasks': self.inapplicable_tasks,
            'adaptation_notes': self.adaptation_notes,
        }


@dataclass
class StepConflict:
    """步骤冲突"""
    conflict_type: ConflictType
    steps: List[str]
    description: str
    severity: str = "medium"
    resolution: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MergedPlan:
    """合并后的综合预案"""
    merged_id: str
    title: str
    description: str
    source_plans: List[str]
    merged_steps: List[TaskStep] = field(default_factory=list)
    conflicts: List[StepConflict] = field(default_factory=list)
    resource_summary: Dict[str, Any] = field(default_factory=dict)
    execution_phases: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'merged_id': self.merged_id, 'title': self.title,
            'description': self.description, 'source_plans': self.source_plans,
            'merged_steps': [s.to_dict() for s in self.merged_steps],
            'conflicts': [c.to_dict() for c in self.conflicts],
            'resource_summary': self.resource_summary,
            'execution_phases': self.execution_phases, 'created_at': self.created_at,
        }


@dataclass
class AnalysisReport:
    """综合研判报告"""
    report_id: str
    query: str
    timestamp: str
    plan_applicabilities: List[PlanApplicability] = field(default_factory=list)
    merged_plan: Optional[MergedPlan] = None
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    risk_assessment: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'report_id': self.report_id, 'query': self.query,
            'timestamp': self.timestamp,
            'plan_applicabilities': [pa.to_dict() for pa in self.plan_applicabilities],
            'merged_plan': self.merged_plan.to_dict() if self.merged_plan else None,
            'summary': self.summary, 'recommendations': self.recommendations,
            'risk_assessment': self.risk_assessment,
        }
