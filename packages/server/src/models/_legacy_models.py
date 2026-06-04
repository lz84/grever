"""
Nexus Reins 数据模型 — 兼容层

枚举类已迁移到 reins.models.enums，此处仅做 re-export。
数据类（Goal, Project, Task, AgentInfo, Dispute 等）仍在此定义。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
import uuid

# === 枚举 re-export（从 models.enums 迁移后的位置） ===
from models.enums import (
    GoalStatus,
    ProjectStatus,
    TaskStatus,
    AgentStatus,
    TriggerMode,
    DisputeType,
    DisputeStatus,
    Priority,
    TaskState,
)

# === 数据类定义 ===

@dataclass
class Goal:
    """目标 (Goal) — 目标管理核心实体"""
    id: str = field(default_factory=lambda: f"goal-{uuid.uuid4().hex[:8]}")
    title: str = ""
    description: str = None
    parent_id: str = None
    status: GoalStatus = GoalStatus.CREATED
    progress: float = 0.0
    task_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime = None

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "description": self.description,
            "parent_id": self.parent_id, "status": self.status.value,
            "progress": self.progress, "task_ids": self.task_ids,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class Project:
    """项目 (Project) — 项目管理核心实体"""
    id: str = field(default_factory=lambda: f"proj-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = None
    goal_id: str = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    members: List[dict] = field(default_factory=list)
    task_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime = None

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "goal_id": self.goal_id, "status": self.status.value,
            "members": self.members, "task_ids": self.task_ids,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class Task:
    """任务 (Task) — 任务管理核心实体"""
    id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    title: str = ""
    description: str = None
    project_id: str = None
    goal_id: str = None
    assigned_agent: str = None
    status: TaskStatus = TaskStatus.TODO
    priority: Priority = Priority.P1
    dependencies: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: datetime = None
    completed_at: datetime = None
    cancelled_at: datetime = None
    blocked_reason: str = None
    estimated_hours: float = None
    actual_hours: float = None
    result: str = None

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "description": self.description,
            "project_id": self.project_id, "goal_id": self.goal_id,
            "assigned_agent": self.assigned_agent, "status": self.status.value,
            "priority": self.priority.value, "dependencies": self.dependencies,
            "depends_on": self.depends_on,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "blocked_reason": self.blocked_reason,
            "estimated_hours": self.estimated_hours, "actual_hours": self.actual_hours,
            "result": self.result,
        }


@dataclass
class AgentInfo:
    """Agent 信息 (AgentInfo) — Agent 注册与发现核心实体"""
    id: str = ""
    name: str = ""
    capabilities: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.OFFLINE
    address: str = None
    metadata: dict = field(default_factory=dict)
    load: int = 0
    current_load: int = 0
    current_tasks: int = 0
    trigger_mode: TriggerMode = TriggerMode.SSE
    poll_interval_seconds: int = 10
    model_name: str = ""
    registered_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "capabilities": self.capabilities,
            "status": self.status.value, "address": self.address,
            "metadata": self.metadata, "load": self.load,
            "current_tasks": self.current_tasks,
            "trigger_mode": self.trigger_mode.value if isinstance(self.trigger_mode, TriggerMode) else self.trigger_mode,
            "poll_interval_seconds": self.poll_interval_seconds,
            "model_name": self.model_name,
            "registered_at": self.registered_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
        }


@dataclass
class Dispute:
    """争议 (Dispute) — 争议管理核心实体"""
    id: str = field(default_factory=lambda: f"disp-{uuid.uuid4().hex[:8]}")
    dispute_type: DisputeType = None
    description: str = ""
    involved_agents: List[str] = field(default_factory=list)
    related_task_id: str = None
    status: DisputeStatus = DisputeStatus.OPEN
    resolution: str = None
    resolved_by: str = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    resolved_at: datetime = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "dispute_type": self.dispute_type.value if self.dispute_type else None,
            "description": self.description,
            "involved_agents": self.involved_agents,
            "related_task_id": self.related_task_id,
            "status": self.status.value,
            "resolution": self.resolution,
            "resolved_by": self.resolved_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class DecomposeResult:
    """任务分解结果"""
    goal_id: str
    tasks: List[Task]
    dependencies: List[dict]
    estimated_total_hours: float


@dataclass
class DiscoverResult:
    """Agent 发现结果"""
    count: int
    agents: List[AgentInfo]
