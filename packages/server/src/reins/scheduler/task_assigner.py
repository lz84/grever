"""
任务分配器 — 向后兼容重导出

Phase 2.3: 实际实现已迁移到 scheduler/assigner/ 子目录。
"""

from reins.scheduler.assigner.task_assigner import TaskAssigner, _assign_agent

__all__ = ["TaskAssigner", "_assign_agent"]
