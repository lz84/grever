"""
执行器模块 — 项目任务执行

- orchestrator: 执行编排器（ProjectExecutor 主类）
- dispatch_coordinator: 派发协调（状态变更、API 调用、日志）
- result_collector: 结果收集（读取结果、更新 DB、触发验证）
"""

from .orchestrator import ProjectExecutor

__all__ = ["ProjectExecutor"]
