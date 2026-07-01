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
from .industry_tag import IndustryCapabilityTag, IndustryPack, IndustryPackVersion
from .skill import Skill
from .knowledge_base import KnowledgeBase
from .knowledge import KnowledgeEntry
from .agent_scheme import AgentScheme
from .agent_scheme_role import AgentSchemeRole
from .human_input import HumanInputRequest
from .execution_log import ExecutionLog
from .task_activity_log import TaskActivityLog
from .goal_iteration import GoalIteration
from .task_comment import TaskComment
from .mcp import MCPServer, MCPTool
from .artifact import Artifact
from .grasp_inject import GraspInjectRule, GraspInjectLog
from .scenario import Scenario, ScenarioProject, ScenarioTask
from .additional_models import (
    Gene, EvolutionEvent, Capsule, A2AMessage,
    TrustEvaluation, Role,
    TaskLabel, TaskRelation,
    Attachment, AttachmentLink,
)

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
    'GoalIteration', 'TaskComment', 'MCPServer', 'MCPTool', 'Artifact',
    'ExecutionLog', 'TaskActivityLog',
    'IndustryCapabilityTag', 'Skill', 'KnowledgeBase', 'KnowledgeEntry', 'AgentScheme', 'AgentSchemeRole', 'GraspInjectRule', 'GraspInjectLog',
    'Gene', 'EvolutionEvent', 'Capsule', 'A2AMessage',
    'TrustEvaluation', 'Role',
    'ScenarioProject', 'ScenarioTask', 'Scenario',
    'TaskLabel', 'TaskRelation',
    'Attachment', 'AttachmentLink',
    # Schemas
    'WorkflowCreate', 'WorkflowUpdate', 'WorkflowResponse',
    'WorkflowStepCreate', 'WorkflowStepUpdate', 'WorkflowStepResponse',
    'SolutionCreate', 'SolutionUpdate', 'SolutionResponse',
    'IterationConstraintCreate', 'IterationConstraintUpdate', 'IterationConstraintResponse',
    'GoalIterationCreate', 'GoalIterationUpdate', 'GoalIterationResponse',
    'TaskCommentCreate', 'TaskCommentUpdate', 'TaskCommentResponse',
    'MCPServerCreate', 'MCPServerUpdate', 'MCPServerResponse',
    'MCPToolCreate', 'MCPToolUpdate', 'MCPToolResponse',
    'ArtifactCreate', 'ArtifactUpdate', 'ArtifactResponse',
    # Dataclasses
    'AgentInfo', 'Dispute', 'DecomposeResult', 'DiscoverResult',
    # Enums
    'TaskStatus', 'GoalStatus', 'ProjectStatus', 'AgentStatus',
    'DisputeType', 'DisputeStatus', 'Priority', 'SolutionStatus',
    'WorkflowStatus', 'WorkflowStepStatus', 'TriggerMode',
]
