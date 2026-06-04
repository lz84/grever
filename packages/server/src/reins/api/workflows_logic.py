"""Workflow 业务逻辑 facade

原 WorkflowsLogic 类已移至 _workflows_logic_core.py。
此文件重新导出该类，并聚合子模块 router 供 workflows.py 使用。
"""
from reins.api._workflows_logic_core import WorkflowsLogic
from reins.api._workflows_activation_routes import router as _activate_router
from reins.api._workflows_progress_routes import router as _progress_router

# Re-export for backwards compat (workflows.py imports this)
__all__ = ["WorkflowsLogic", "router"]

# Facade router: 聚合所有子模块 router
from fastapi import APIRouter
router = APIRouter()
router.include_router(_activate_router)
router.include_router(_progress_router)
