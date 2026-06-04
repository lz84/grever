"""Reins models package — ORM models + dataclasses + enums"""

# === ORM models (from submodules) ===
from .task import Task
from .task import TaskStatus as _TaskStatus
from .task import TaskPriority
from .goal import Goal
from .goal import GoalStatus as _GoalStatus
from .project import Project
from .agent import Agent, AgentTagWeight
from .workflow import (
    Workflow,
    WorkflowStep,
    WorkflowStatus,
    WorkflowStepStatus,
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowStepCreate,
    WorkflowStepUpdate,
    WorkflowStepResponse,
)
from .solution import Solution
from .solution import SolutionStatus as _SolutionStatus
from .iteration_constraint import IterationConstraint
from .industry_tag import IndustryCapabilityTag, IndustryPack, IndustryPackContent

# Aliases
SqlWorkflow = Workflow
SqlWorkflowStep = WorkflowStep

# === Enums from centralized enums.py ===
from .enums import (
    AgentStatus,
    DisputeStatus,
    DisputeType,
    GoalStatus as _LegacyGoalStatus,
    Priority,
    ProjectStatus,
    TaskStatus as _EnumTaskStatus,
    TriggerMode,
)

# Aliases for compatibility (non-lazy)
TaskStatus = _TaskStatus  # 使用 task.py 的完整实现（含 FAILED/TIMEOUT），不能用 legacy_models 的覆盖
GoalStatus = _LegacyGoalStatus
DisputeType = DisputeType
DisputeStatus = DisputeStatus
AgentStatus = AgentStatus
ProjectStatus = ProjectStatus
Priority = Priority
SolutionStatus = _SolutionStatus
TriggerMode = TriggerMode

# === Dataclasses from _legacy_models (compat layer) ===
# Lazy import to avoid circular dependency:
# models.__init__ → reins.__init__ → services.goal_manager → models → circular
# These are resolved via __getattr__ on first access.
_lm = None


def __getattr__(name: str):
    global _lm
    if name in ("AgentInfo", "Dispute", "DecomposeResult", "DiscoverResult"):
        if _lm is None:
            from models._legacy_models import AgentInfo, Dispute, DecomposeResult, DiscoverResult
            _lm = type('_lm', (), {
                'AgentInfo': AgentInfo,
                'Dispute': Dispute,
                'DecomposeResult': DecomposeResult,
                'DiscoverResult': DiscoverResult,
            })
        return getattr(_lm, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # ORM
    'Task', 'Goal', 'Project', 'Agent', 'AgentTagWeight', 'Workflow', 'WorkflowStep',
    'SqlWorkflow', 'SqlWorkflowStep', 'Solution', 'IterationConstraint',
    # Schemas
    'WorkflowCreate', 'WorkflowUpdate', 'WorkflowResponse',
    'WorkflowStepCreate', 'WorkflowStepUpdate', 'WorkflowStepResponse',
    'SolutionCreate', 'SolutionUpdate', 'SolutionResponse',
    'IterationConstraintCreate', 'IterationConstraintUpdate', 'IterationConstraintResponse',
    # Dataclasses
    'AgentInfo', 'Dispute', 'DecomposeResult', 'DiscoverResult',
    # Enums
    'TaskStatus', 'GoalStatus', 'ProjectStatus', 'AgentStatus',
    'DisputeType', 'DisputeStatus', 'Priority', 'SolutionStatus',
    'WorkflowStatus', 'WorkflowStepStatus', 'TriggerMode',
]
