"""
目标管理 (Goal Management)
负责目标的创建、分解、跟踪、调整

2026-04-25 精简：所有操作已迁移到 ReinsServer + GoalRepository。
此类保留仅用于向后兼容。
"""

from typing import List, Optional
from models import Goal, GoalStatus, Task
from services.task_manager import TaskManager

class GoalManager:
    """
    目标管理器（已废弃）

    2026-04-25 重构：Goal CRUD 全部走 DB repository (ReinsServer 直接调用)。
    Goal 分解逻辑由 goals_router + goal_decomposition service 处理。
    此类保留仅用于向后兼容。
    """

    def __init__(self, task_manager: TaskManager = None, goal_repository=None):
        self._task_manager = task_manager
        self._goal_repository = goal_repository
