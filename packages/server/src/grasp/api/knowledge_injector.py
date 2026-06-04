"""知识注入 API - Facade（合并子模块路由）"""

from fastapi import APIRouter

from .knowledge_injector_routes import router as _inject_router

router = APIRouter(prefix="/api/v1/grasp/inject", tags=["grasp-inject"])
router.include_router(_inject_router)
