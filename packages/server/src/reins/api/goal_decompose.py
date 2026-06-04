"""
目标自动分解 API — Facade

MAK-226: 目标自动分解 + Grasp 认知注入
子模块:
  - goal_decompose_helpers: 辅助函数与提示词
  - goal_decompose_preview: 预览端点
  - goal_decompose_submit: 提交端点
"""

from fastapi import APIRouter

from .goal_decompose_preview import router as preview_router
from .goal_decompose_submit import router as submit_router

router = APIRouter(prefix="/api/v1/goals", tags=["goals"])
router.include_router(preview_router)
router.include_router(submit_router)
