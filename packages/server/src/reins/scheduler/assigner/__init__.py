"""
任务分配模块

- task_assigner: 任务分配逻辑
"""

from .task_assigner import TaskAssigner

__all__ = ["TaskAssigner"]


# Compatibility alias
from reins.core.engine import DAGScheduler as TaskManager
