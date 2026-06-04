"""Task API CRUD endpoints — Facade (split into sub-modules)

Sub-modules:
  - tasks_crud_helpers:  shared utilities (sync depends_on, agent probe, unblock, cleanup)
  - tasks_crud_read:     GET /{task_id}
  - tasks_crud_create:   POST /
  - tasks_crud_update:   PUT /{task_id}, PATCH /{task_id}
  - tasks_crud_delete:   DELETE /{task_id}
"""
from fastapi import APIRouter
from .tasks_crud_read import router as read_router
from .tasks_crud_create import router as create_router
from .tasks_crud_update import router as update_router
from .tasks_crud_delete import router as delete_router

router = APIRouter(tags=["tasks"])
router.include_router(read_router)
router.include_router(create_router)
router.include_router(update_router)
router.include_router(delete_router)
