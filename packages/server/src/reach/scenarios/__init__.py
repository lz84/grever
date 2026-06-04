"""
场景模块 — Scenario 管理

- crud: helpers + 写端点
- projects: 项目/任务 CRUD
- read: 读端点（list/get/status/fullset）
"""

from .crud import router as crud_router
from .projects import router as projects_router
from .read import router as read_router

__all__ = ["crud_router", "projects_router", "read_router"]
