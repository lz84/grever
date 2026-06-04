"""Settings API - Facade（合并子模块路由）"""

from fastapi import APIRouter

from .settings_routes import router as _settings_router

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])
router.include_router(_settings_router)
