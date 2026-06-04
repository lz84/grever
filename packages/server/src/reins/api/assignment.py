"""Assignment API - Facade (MAK-214)

本文件重导出所有 assignment 相关接口，保持原有 import 路径兼容。
业务逻辑已拆分至：
- assignment_services.py：纯函数（模型连通性检查、任务分配算法、任务上下文）
- assignment_endpoints.py：FastAPI 路由及端点
"""

from reins.api.assignment_services import (
    check_model_connectivity,
    matches_capabilities,
    get_load_score,
    assign_tasks_to_agent,
    get_task_context,
)
from reins.api.assignment_endpoints import router

__all__ = [
    "router",
    "check_model_connectivity",
    "matches_capabilities",
    "get_load_score",
    "assign_tasks_to_agent",
    "get_task_context",
]