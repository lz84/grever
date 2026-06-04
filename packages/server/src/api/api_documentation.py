"""API Documentation (Facade) — merges endpoint listing & features routers."""
from fastapi import APIRouter
from .api_docs_endpoints import router as endpoints_router
from .api_docs_features import router as features_router

router = APIRouter(prefix="/api/v1/docs", tags=["documentation"])

router.include_router(endpoints_router)
router.include_router(features_router)
