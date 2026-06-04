"""Goals API (Facade) — merges list, CRUD, decomposition & verifier routers."""
from fastapi import APIRouter

from .goals_list import router as list_router
from .goals_crud import router as crud_router
from .goals_decompose import router as decompose_router

router = APIRouter(prefix="/api/v1/goals", tags=["goals"])

router.include_router(list_router)
router.include_router(crud_router)
router.include_router(decompose_router)
