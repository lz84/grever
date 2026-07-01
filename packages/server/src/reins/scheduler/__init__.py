"""
Grever 调度引擎

Phase 1: 包结构 + 统计类 + 调度器占位
Phase 2+: 健康度管理 + 任务回收 + 任务分配 + 依赖解析
"""

from reins.scheduler.stats import SchedulerStats
from reins.scheduler.core import GreverScheduler
from reins.scheduler.optimization_loop import OptimizationLoop

# 全局调度器实例（None 表示未启动）
_scheduler: GreverScheduler | None = None

def get_scheduler() -> GreverScheduler | None:
    """获取全局调度器实例"""
    return _scheduler

def set_scheduler(scheduler: GreverScheduler) -> None:
    """设置全局调度器实例"""
    global _scheduler
    _scheduler = scheduler

__all__ = ["GreverScheduler", "SchedulerStats", "OptimizationLoop", "get_scheduler", "set_scheduler"]
