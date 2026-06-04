"""
任务管理 (Task Management)
负责任务的创建、分配、状态追踪、依赖管理

2026-04-25 重构：所有写操作改为 DB repository，不再维护内存字典。
"""

from typing import List, Optional
from models import Task, TaskStatus, Priority
from datetime import datetime
from persistence.repository import TaskRepository

class TaskManager:
    """
    任务管理器

    2026-04-25 重构：所有操作通过 TaskRepository 读写 DB。
    不再维护 _tasks 内存字典。
    """

    def __init__(self, repository: TaskRepository = None):
        self._repository = repository

    def create_task(
        self,
        title: str,
        description: str = None,
        project_id: str = None,
        goal_id: str = None,
        assigned_agent: str = None,
        priority: Priority = Priority.P1,
        estimated_hours: float = None,
    ) -> Task:
        """创建任务 — 写入 DB"""
        if not self._repository:
            raise RuntimeError("TaskManager requires a TaskRepository")
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
        self._repository.save(task)
        return task

    def update_status(self, task_id: str, status: TaskStatus) -> Task:
        """
        更新任务状态（含状态机逻辑）— 写入 DB

        状态转换规则：
        - TODO → IN_PROGRESS: 记录 started_at
        - ANY → DONE: 记录 completed_at
        """
        if not self._repository:
            raise RuntimeError("TaskManager requires a TaskRepository")
        task = self._repository.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        old_status = task.status
        task.status = status
        task.updated_at = datetime.now()

        if status == TaskStatus.IN_PROGRESS and old_status == TaskStatus.TODO:
            task.started_at = datetime.now()
        elif status == TaskStatus.DONE:
            task.completed_at = datetime.now()

        self._repository.save(task)
        return task

    def add_dependency(self, task_id: str, depends_on: str) -> Task:
        """添加任务依赖 — 写入 DB"""
        if not self._repository:
            raise RuntimeError("TaskManager requires a TaskRepository")
        task = self._repository.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if depends_on not in task.dependencies:
            task.dependencies.append(depends_on)
            task.updated_at = datetime.now()
            self._repository.save(task)

        return task

    def remove_dependency(self, task_id: str, depends_on: str) -> Task:
        """移除任务依赖 — 写入 DB"""
        if not self._repository:
            raise RuntimeError("TaskManager requires a TaskRepository")
        task = self._repository.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if depends_on in task.dependencies:
            task.dependencies.remove(depends_on)
            task.updated_at = datetime.now()
            self._repository.save(task)

        return task

    # ========== 子任务管理 ==========

    def add_subtask(self, task_id: str, subtask_id: str) -> Task:
        """添加子任务 — 写入 DB"""
        if not self._repository:
            raise RuntimeError("TaskManager requires a TaskRepository")
        parent = self._repository.get(task_id)
        if not parent:
            raise ValueError(f"Task not found: {task_id}")

        if subtask_id not in parent.subtask_ids:
            parent.subtask_ids.append(subtask_id)
            parent.updated_at = datetime.now()
            self._repository.save(parent)

        # 设置子任务的 parent_id
        child = self._repository.get(subtask_id)
        if child and child.parent_id != task_id:
            child.parent_id = task_id
            child.updated_at = datetime.now()
            self._repository.save(child)

        return parent

    def remove_subtask(self, task_id: str, subtask_id: str) -> Task:
        """移除子任务 — 写入 DB"""
        if not self._repository:
            raise RuntimeError("TaskManager requires a TaskRepository")
        parent = self._repository.get(task_id)
        if not parent:
            raise ValueError(f"Task not found: {task_id}")

        if subtask_id in parent.subtask_ids:
            parent.subtask_ids.remove(subtask_id)
            parent.updated_at = datetime.now()
            self._repository.save(parent)

        child = self._repository.get(subtask_id)
        if child and child.parent_id == task_id:
            child.parent_id = None
            child.updated_at = datetime.now()
            self._repository.save(child)

        return parent

    def get_subtasks(self, task_id: str) -> List[Task]:
        """获取子任务列表 — 查 DB"""
        if not self._repository:
            raise RuntimeError("TaskManager requires a TaskRepository")
        parent = self._repository.get(task_id)
        if not parent:
            raise ValueError(f"Task not found: {task_id}")

        subtasks = []
        for sid in parent.subtask_ids:
            child = self._repository.get(sid)
            if child:
                subtasks.append(child)
        return subtasks

    def get_parent(self, task_id: str) -> Optional[Task]:
        """获取父任务 — 查 DB"""
        if not self._repository:
            raise RuntimeError("TaskManager requires a TaskRepository")
        task = self._repository.get(task_id)
        if not task or not task.parent_id:
            return None
        return self._repository.get(task.parent_id)
