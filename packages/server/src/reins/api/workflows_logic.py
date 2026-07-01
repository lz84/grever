"""Workflow 业务逻辑 facade

原 WorkflowsLogic 类已移至 _workflows_logic_core.py。
此文件重新导出该类，并聚合子模块 router 供 workflows.py 使用。
"""
from reins.api._workflows_logic_core import WorkflowsLogic

# Re-export for backwards compat (workflows.py imports this)
__all__ = ["WorkflowsLogic", "router"]

# Facade router: 聚合所有子模块 router
# 注: _workflows_activation_routes 和 _workflows_progress_routes 尚未实现，
# 暂不挂载子路由，待功能开发时再接入
from fastapi import APIRouter
router = APIRouter()
