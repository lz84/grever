"""Task API router — Facade that imports all submodules and merges their routers.

This file replaces the old monolithic tasks.py.
Submodules (all <500 lines):
  - tasks_crud_helpers:  shared utilities (sync depends_on, agent probe, unblock, cleanup)
  - tasks_crud_read:     GET /{task_id}
  - tasks_crud_create:   POST /
  - tasks_crud_update:   PUT /{task_id}, PATCH /{task_id}
  - tasks_crud_delete:   DELETE /{task_id}
  - tasks_list:          GET / (list tasks)
"""
from fastapi import APIRouter

from reins.api.tasks_crud_read import router as tasks_crud_read_router
from reins.api.tasks_crud_create import router as tasks_crud_create_router
from reins.api.tasks_crud_update import router as tasks_crud_update_router
from reins.api.tasks_crud_delete import router as tasks_crud_delete_router
from reins.api.tasks_list import router as tasks_list_router

# Merge all sub-module routers into one
router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

# Sprint 104: Register list endpoint with trailing slash (included from tasks_list_router)
# AND without trailing slash (direct route) — frontend calls without trailing slash
# and FastAPI 307 redirect causes issues with some HTTP clients
from reins.api.tasks_list import list_tasks
router.add_api_route("", list_tasks, methods=["GET"], tags=["tasks"])

router.include_router(tasks_list_router)
router.include_router(tasks_crud_read_router)
router.include_router(tasks_crud_create_router)
router.include_router(tasks_crud_update_router)
router.include_router(tasks_crud_delete_router)

__all__ = ["router"]