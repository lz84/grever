"""
项目执行器 — 单项目执行逻辑（向后兼容重导出）

Phase 2.3: 实际实现已迁移到 executor/ 子模块：
- executor/orchestrator.py — 执行编排器
- executor/dispatch_coordinator.py — 派发协调
- executor/result_collector.py — 结果收集
"""

from reins.scheduler.executor.orchestrator import ProjectExecutor

__all__ = ["ProjectExecutor"]
