"""
task_runner 兼容层 — 为 executor 子模块提供导入

从 task_runner 模块导入需要的函数，避免循环依赖。
"""

from reins.scheduler.task_runner import (
    launch,
    check_completed,
    read_result,
    write_result_file,
)

__all__ = ["launch", "check_completed", "read_result", "write_result_file"]
