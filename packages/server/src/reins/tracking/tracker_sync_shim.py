"""
同步执行追踪器 — 向后兼容重导出

Phase 2.3: 实际实现已迁移到 tracking/ 子模块：
- tracking/tracker.py — 异步追踪器
- tracking/sync.py — 同步追踪器
"""

from reins.tracking.sync import ExecutionTrackerSync

__all__ = ["ExecutionTrackerSync"]


# Compatibility import
from reins.tracking.sync import TraceEvent
