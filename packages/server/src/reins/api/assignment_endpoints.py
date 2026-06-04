"""Assignment API endpoints (MAK-214) — Facade

Imports and merges routers from split modules.
"""

from fastapi import APIRouter

from reins.api.assignment_context import router as context_router
from reins.api.assignment_pending_tasks import router as pending_tasks_router
from reins.api.assignment_execution_logs import router as execution_logs_router
from reins.api.assignment_recover_timeout import router as recover_timeout_router

router = APIRouter(prefix="/api/v1", tags=["assignments"])

router.include_router(context_router)
router.include_router(pending_tasks_router)
router.include_router(execution_logs_router)
router.include_router(recover_timeout_router)
