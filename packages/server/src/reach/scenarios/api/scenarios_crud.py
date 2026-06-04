"""
Scenario CRUD & Review API — 向后兼容重导出

Phase 2.3: 实际实现已迁移到 scenarios/ 子模块：
- scenarios/crud.py — helpers + 写端点
- scenarios/projects.py — 项目/任务 CRUD
- scenarios/read.py — 读端点（list/get/status/fullset）

此模块聚合所有 router 以保持向后兼容。
"""

from fastapi import APIRouter

from reach.scenarios.crud import router as crud_router
from reach.scenarios.projects import router as projects_router
from reach.scenarios.read import router as read_router

# 聚合所有路由到一个 router（向后兼容）
router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])

# 注册子路由
for sub_router in (crud_router, projects_router, read_router):
    router.include_router(sub_router)

__all__ = ["router"]
