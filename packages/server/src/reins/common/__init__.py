"""
Nexus Reins (御) - Agent 协同驾驭框架
服务端实现

提供 6 大核心职责：
1. 目标管理 (Goal Management)
2. 项目管理 (Project Management)
3. 任务管理 (Task Management)
4. Agent 注册 (Agent Registration)
5. Agent 发现 (Agent Discovery)
6. 争议管理 (Dispute Management)
"""
from __future__ import annotations

import sys
import os

# Direct imports to avoid __getattr__ circular import issues
# These are imported here to avoid NameError inside class methods
from services.goal_manager import GoalManager
from services.project_manager import ProjectManager
from services.task_manager import TaskManager
from services.dispute_manager import DisputeManager
from reins.scheduler.assigner.agent_registry import AgentRegistry
from reins.scheduler.assigner.agent_discovery import AgentDiscovery
from reins.common.grasp_client.caller import GraspClient
from reins.tracking.tracker_sync_shim import ExecutionTrackerSync

# 添加父目录到路径以支持相对导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional, List

from sqlalchemy import text
from persistence.database import DatabaseManager
from persistence.base import DatabaseConfig
from reins.common.grasp_client.caller import get_grasp_client

__version__ = "0.1.0"
__author__ = "Nexus Team"

__version__ = "0.1.0"
__author__ = "Nexus Team"

# Lazy imports to avoid circular dependency with models.__init__
def __getattr__(name: str):
    if name == "GoalManager":
        from services.goal_manager import GoalManager; return GoalManager
    if name == "ProjectManager":
        from services.project_manager import ProjectManager; return ProjectManager
    if name == "TaskManager":
        from services.task_manager import TaskManager; return TaskManager
    if name == "AgentRegistry":
        from reins.scheduler.assigner.agent_registry import AgentRegistry; return AgentRegistry
    if name == "AgentDiscovery":
        from reins.scheduler.assigner.agent_discovery import AgentDiscovery; return AgentDiscovery
    if name == "DisputeManager":
        from services.dispute_manager import DisputeManager; return DisputeManager
    if name == "Goal":
        from models import Goal; return Goal
    if name == "Project":
        from models import Project; return Project
    if name == "Task":
        from models import Task; return Task
    if name == "AgentInfo":
        from models import AgentInfo; return AgentInfo
    if name == "Dispute":
        from models import Dispute; return Dispute
    if name == "GoalStatus":
        from models import GoalStatus; return GoalStatus
    if name == "ProjectStatus":
        from models import ProjectStatus; return ProjectStatus
    if name == "TaskStatus":
        from models import TaskStatus; return TaskStatus
    if name == "AgentStatus":
        from models import AgentStatus; return AgentStatus
    if name == "TriggerMode":
        from models import TriggerMode; return TriggerMode
    if name == "DisputeType":
        from models import DisputeType; return DisputeType
    if name == "DisputeStatus":
        from models import DisputeStatus; return DisputeStatus
    if name == "Priority":
        from models import Priority; return Priority
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Reins Server 主类 - 整合 6 大职责
class ReinsServer:
    """
    Reins 服务端主类
    整合 6 大核心管理职责

    2026-04-25 重构：Goals/Projects/Tasks/Disputes 全部走 DB repository，
    不再使用内存管理器。Agent 保留内存（background_tasks 依赖）。
    """

    def __init__(self, db_config: DatabaseConfig = None, grasp_url: str = "http://grasp:8000"):
        # 初始化数据库
        self._db_config = db_config or DatabaseConfig()
        self._db_manager = DatabaseManager(self._db_config)

        # 创建持久化仓库
        from persistence.repository import (
            GoalRepository,
            ProjectRepository,
            TaskRepository,
            AgentRepository,
            DisputeRepository,
        )

        self._goal_repository = GoalRepository(self._db_manager.engine)
        self._project_repository = ProjectRepository(self._db_manager.engine)
        self._task_repository = TaskRepository(self._db_manager.engine)
        self._agent_repository = AgentRepository(self._db_manager.engine)
        self._dispute_repository = DisputeRepository(self._db_manager.engine)

        # 初始化 Grasp 客户端
        from reins.common.grasp_client.caller import GraspClient
        self._grasp_client = GraspClient(grasp_url)

        # 初始化管理器（精简版，不再作为主数据源）
        self.task_manager = TaskManager(self._task_repository)
        self.goal_manager = GoalManager(
            task_manager=self.task_manager,
            goal_repository=self._goal_repository,
        )
        self.project_manager = ProjectManager()
        self.agent_registry = AgentRegistry()
        self.agent_discovery = AgentDiscovery(self.agent_registry)
        self.dispute_manager = DisputeManager()

        # 执行追踪器
        from reins.tracking.tracker_sync_shim import ExecutionTrackerSync
        self.tracker = ExecutionTrackerSync()

        # 创建数据库表
        self._db_manager.create_tables()

    # ========== 目标管理（直接查/写 DB） ==========

    def create_goal(self, title: str, description: str = None, parent_id: str = None) -> Goal:
        """创建目标 — 直接写 DB"""
        goal = Goal(
            title=title,
            description=description,
            parent_id=parent_id,
            status=GoalStatus.CREATED,
        )
        self._goal_repository.save(goal)
        return goal

    def get_goal(self, goal_id: str) -> Goal:
        """获取目标 — 直接查 DB"""
        return self._goal_repository.get(goal_id)

    def list_goals(self, status: GoalStatus = None) -> list:
        """列出目标 — 直接查 DB"""
        return self._goal_repository.list(status)

    def update_goal_status(self, goal_id: str, status: GoalStatus) -> Goal:
        """更新目标状态 — 直接查 DB + save"""
        goal = self._goal_repository.get(goal_id)
        if not goal:
            raise ValueError(f"Goal not found: {goal_id}")
        goal.status = status
        if status == GoalStatus.COMPLETED:
            from datetime import datetime
            goal.completed_at = datetime.now()
        self._goal_repository.save(goal)
        return goal

    def decompose_goal(self, goal_id: str, agent_id: str = None) -> list:
        """分解目标为任务 — 通过 goal_decomposition service（兼容层）"""
        goal = self._goal_repository.get(goal_id)
        if not goal:
            raise ValueError(f"Goal not found: {goal_id}")
        from services.goal_decomposition import decompose_and_create_tasks
        from reins.common.database import get_db
        with get_db() as db:
            tasks = decompose_and_create_tasks(
                goal_id=goal_id,
                goal_title=goal.title,
                goal_description=goal.description,
                db=db,
            )
        return tasks

    # ========== 项目管理（直接查/写 DB） ==========

    def create_project(self, name: str, description: str = None, goal_id: str = None) -> Project:
        """创建项目 — 直接写 DB"""
        from models import ProjectStatus as PS
        project = Project(
            name=name, description=description, goal_id=goal_id, status=PS.ACTIVE,
        )
        self._project_repository.save(project)
        return project

    def get_project(self, project_id: str) -> Project:
        """获取项目 — 直接查 DB"""
        return self._project_repository.get(project_id)

    def list_projects(self, status: ProjectStatus = None) -> list:
        """列出项目 — 直接查 DB"""
        return self._project_repository.list(status)

    def add_project_member(self, project_id: str, agent_id: str, role: str = "member") -> Project:
        """添加项目成员 — 直接查 DB + save"""
        project = self._project_repository.get(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")
        # 检查是否已存在
        for member in project.members:
            if member.get("agent_id") == agent_id:
                member["role"] = role
                self._project_repository.save(project)
                return project
        # 添加新成员
        project.members.append({"agent_id": agent_id, "role": role})
        self._project_repository.save(project)
        return project

    def get_project_progress(self, project_id: str) -> float:
        """获取项目进度 — 直接查 DB 统计任务"""
        from sqlalchemy import text
        project = self._project_repository.get(project_id)
        if not project:
            return 0.0
        with self._db_manager.engine.connect() as conn:
            # 统计该项目下已完成任务占比
            total = conn.execute(text(
                "SELECT COUNT(*) FROM tasks WHERE project_id = :pid"
            ), {"pid": project_id}).scalar() or 0
            if total == 0:
                return 0.0
            done = conn.execute(text(
                "SELECT COUNT(*) FROM tasks WHERE project_id = :pid AND status IN ('done', 'completed')"
            ), {"pid": project_id}).scalar() or 0
            return round(done / total * 100, 2)

    # ========== 任务管理（直接查/写 DB） ==========

    def create_task(
        self,
        title: str,
        description: str = None,
        project_id: str = None,
        goal_id: str = None,
        assigned_agent: str = None,
        priority=None,
        estimated_hours: float = None,
    ) -> Task:
        """创建任务 — 直接写 DB"""
        task = Task(
            title=title,
            description=description,
            project_id=project_id,
            goal_id=goal_id,
            assigned_agent=assigned_agent,
            status=TaskStatus.TODO,
            priority=priority,
            estimated_hours=estimated_hours,
        )
        self._task_repository.save(task)
        return task

    def get_task(self, task_id: str) -> Task:
        """获取任务 — 直接查 DB"""
        return self._task_repository.get(task_id)

    def list_tasks(self, status: TaskStatus = None, project_id: str = None, assigned_agent: str = None) -> list:
        """列出任务 — 直接查 DB"""
        return self._task_repository.list(status, project_id, assigned_agent)

    def assign_task(self, task_id: str, agent_id: str) -> Task:
        """分配任务 — 直接查 DB + save"""
        task = self._task_repository.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        task.assigned_agent = agent_id
        self._task_repository.save(task)
        return task

    def update_task_status(self, task_id: str, status: TaskStatus) -> Task:
        """更新任务状态 — 直接查 DB + save"""
        task = self._task_repository.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        old_status = task.status
        task.status = status
        task.updated_at = __import__('datetime').datetime.now()

        if status == TaskStatus.IN_PROGRESS and old_status == TaskStatus.TODO:
            task.started_at = __import__('datetime').datetime.now()
        elif status == TaskStatus.DONE:
            task.completed_at = __import__('datetime').datetime.now()

        self._task_repository.save(task)
        return task

    def add_task_dependency(self, task_id: str, depends_on: str) -> Task:
        """添加任务依赖 — 直接操作 DB"""
        task = self._task_repository.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if depends_on not in task.dependencies:
            task.dependencies.append(depends_on)
            task.updated_at = __import__('datetime').datetime.now()
            self._task_repository.save(task)

        return task

    def add_subtask(self, task_id: str, subtask_id: str) -> Task:
        """添加子任务 — 直接操作 DB"""
        from datetime import datetime
        parent = self._task_repository.get(task_id)
        if not parent:
            raise ValueError(f"Task not found: {task_id}")

        if subtask_id not in parent.subtask_ids:
            parent.subtask_ids.append(subtask_id)
            parent.updated_at = datetime.now()
            self._task_repository.save(parent)

        # 设置子任务的 parent_id
        child = self._task_repository.get(subtask_id)
        if child and child.parent_id != task_id:
            child.parent_id = task_id
            child.updated_at = datetime.now()
            self._task_repository.save(child)

        return parent

    def remove_subtask(self, task_id: str, subtask_id: str) -> Task:
        """移除子任务 — 直接操作 DB"""
        from datetime import datetime
        parent = self._task_repository.get(task_id)
        if not parent:
            raise ValueError(f"Task not found: {task_id}")

        if subtask_id in parent.subtask_ids:
            parent.subtask_ids.remove(subtask_id)
            parent.updated_at = datetime.now()
            self._task_repository.save(parent)

        child = self._task_repository.get(subtask_id)
        if child and child.parent_id == task_id:
            child.parent_id = None
            child.updated_at = datetime.now()
            self._task_repository.save(child)

        return parent

    def get_subtasks(self, task_id: str) -> List[Task]:
        """获取子任务列表 — 查 DB"""
        parent = self._task_repository.get(task_id)
        if not parent:
            raise ValueError(f"Task not found: {task_id}")

        subtasks = []
        for sid in parent.subtask_ids:
            child = self._task_repository.get(sid)
            if child:
                subtasks.append(child)
        return subtasks

    def get_parent(self, task_id: str) -> Optional[Task]:
        """获取父任务 — 查 DB"""
        task = self._task_repository.get(task_id)
        if not task or not task.parent_id:
            return None
        return self._task_repository.get(task.parent_id)

    # ========== Agent 注册（保留内存） ==========

    def register_agent(
        self,
        agent_id: str,
        name: str,
        capabilities: list,
        address: str = None,
        metadata: dict = None,
        trigger_mode: "TriggerMode" = None,
        poll_interval_seconds: int = 10,
        model_name: str = "",
        last_heartbeat: "datetime" = None,
    ) -> AgentInfo:
        """注册 Agent — DB 直接写入（AgentRegistry 已是 DB 驱动）
        
        last_heartbeat: 可选，传入 DB 中已有的 heartbeat 以避免被覆盖
        """
        from models import TriggerMode as TM
        if trigger_mode is None:
            trigger_mode = TM.SSE
        # AgentRegistry.register() 已经是 DB UPSERT，不需要第二次写入
        return self.agent_registry.register(
            agent_id, name, capabilities, address, metadata,
            trigger_mode=trigger_mode,
            poll_interval_seconds=poll_interval_seconds,
            model_name=model_name,
            last_heartbeat=last_heartbeat,
        )

    def unregister_agent(self, agent_id: str, reason: str = None) -> bool:
        """注销 Agent — AgentRegistry 已 DB 驱动，直接调用即可"""
        # AgentRegistry.unregister() 已写 DB（UPDATE status=offline）
        return self.agent_registry.unregister(agent_id, reason)

    def heartbeat_agent(self, agent_id: str, status: dict = None) -> bool:
        """Agent 心跳 — AgentRegistry 已 DB 驱动，直接调用即可"""
        # AgentRegistry.heartbeat() 已直接写 DB
        return self.agent_registry.heartbeat(agent_id, status)
        from sqlalchemy import text
        from datetime import datetime
        
        # 构建更新字段
        # 兼容 status 和 state 两种字段名
        _status = status.get('status') if status else None
        if not _status and status and status.get('state'):
            _status = status['state']
        if not _status:
            _status = 'online'
        
        # Phase 1.1: 自动计算 load = min(100, current_tasks / max_concurrent_tasks * 100)
        current_tasks = status.get('current_tasks') if status and status.get('current_tasks') is not None else None
        max_concurrent_tasks = 5  # 默认值，查询获取实际值
        
    def get_registered_agents(self) -> list:
        """获取已注册 Agent"""
        return self.agent_registry.list_agents()

    # ========== Agent 发现 ==========

    def discover_agents(self, capabilities: list = None, status: AgentStatus = None, max_load: int = None) -> list:
        """发现 Agent"""
        return self.agent_discovery.discover(capabilities, status, max_load)

    def find_agent(self, agent_id: str) -> AgentInfo:
        """查找特定 Agent"""
        return self.agent_discovery.find(agent_id)

    # ========== 争议管理（直接查/写 DB） ==========

    def raise_dispute(
        self,
        dispute_type: DisputeType,
        description: str,
        involved_agents: list,
        related_task_id: str = None,
    ) -> Dispute:
        """发起争议 — 直接写 DB"""
        dispute = Dispute(
            dispute_type=dispute_type,
            description=description,
            involved_agents=involved_agents,
            related_task_id=related_task_id,
            status=DisputeStatus.OPEN,
        )
        self._dispute_repository.save(dispute)
        return dispute

    def resolve_dispute(self, dispute_id: str, resolution: str, resolved_by: str = None) -> Dispute:
        """解决争议 — 直接写 DB"""
        from datetime import datetime
        dispute = self._dispute_repository.get(dispute_id)
        if not dispute:
            raise ValueError(f"Dispute not found: {dispute_id}")

        dispute.status = DisputeStatus.RESOLVED
        dispute.resolution = resolution
        dispute.resolved_by = resolved_by
        dispute.resolved_at = datetime.now()
        dispute.updated_at = datetime.now()
        self._dispute_repository.save(dispute)
        return dispute

    def get_dispute(self, dispute_id: str) -> Dispute:
        """获取争议 — 查 DB"""
        return self._dispute_repository.get(dispute_id)

    def list_disputes(self, status: DisputeStatus = None) -> list:
        """列出争议 — 查 DB"""
        return self._dispute_repository.list(status)

    # ========== 执行追踪 ==========

    def start_trace(self, workflow_id: str, task_id: str, task_title: str):
        """开始追踪"""
        return self.tracker.start_trace(workflow_id, task_id, task_title)

    def complete_trace(
        self,
        task_id: str,
        final_state: str,
        success: bool,
        result: dict = None,
        error_message: str = None,
        cognitions_used: int = 0,
        context_size_bytes: int = 0,
    ):
        """完成追踪"""
        return self.tracker.complete_trace(
            task_id=task_id,
            final_state=final_state,
            success=success,
            result=result,
            error_message=error_message,
            cognitions_used=cognitions_used,
            context_size_bytes=context_size_bytes,
        )

    def get_trace(self, task_id: str):
        """获取追踪"""
        return self.tracker.get_trace(task_id)

    def get_report(self, task_id: str):
        """获取报告"""
        return self.tracker.get_report(task_id)

__all__ = [
    "ReinsServer",
    "GoalManager",
    "ProjectManager",
    "TaskManager",
    "AgentRegistry",
    "AgentDiscovery",
    "DisputeManager",
    # Models
    "Goal",
    "Project",
    "Task",
    "AgentInfo",
    "Dispute",
    "GoalStatus",
    "ProjectStatus",
    "TaskStatus",
    "AgentStatus",
    "DisputeType",
    "DisputeStatus",
]
