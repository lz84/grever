"""Task API router — Facade that imports all submodules and merges their routers.

This file replaces the old monolithic tasks.py.
Submodules (all <500 lines):
  - tasks_crud_helpers:  shared utilities (sync depends_on, agent probe, unblock, cleanup)
  - tasks_crud_read:     GET /{task_id}
  - tasks_crud_create:   POST /
  - tasks_crud_update:   PUT /{task_id}, PATCH /{task_id}
  - tasks_crud_delete:   DELETE /{task_id}
  - tasks_list:          GET / (list tasks)
  - tasks_state:         state management + GET /statuses
  - tasks_lifecycle:     POST /{task_id}/pause/resume/restart/terminate/takeover
  - tasks_review:        /{task_id}/verify, /review, /verifier, /verifications
  - tasks_execution:     /{task_id}/progress, /fail, /failure-log, /retry
  - tasks_labels:        /labels/all, /{task_id}/labels, /{task_id}/labels/{label_id}
"""
from fastapi import APIRouter

from reins.api.tasks_crud_read import router as tasks_crud_read_router
from reins.api.tasks_crud_create import router as tasks_crud_create_router
from reins.api.tasks_crud_update import router as tasks_crud_update_router
from reins.api.tasks_crud_delete import router as tasks_crud_delete_router
from reins.api.tasks_list import router as tasks_list_router
from reins.api.tasks_state import router as tasks_state_router
from reins.api.tasks_lifecycle import router as tasks_lifecycle_router
from reins.api.tasks_review import router as tasks_review_router
from reins.api.tasks_execution import router as tasks_execution_router
from reins.api.tasks_labels import router as tasks_labels_router

# Merge all sub-module routers into one
router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

# Sprint 104: Register list endpoint with trailing slash (included from tasks_list_router)
# AND without trailing slash (direct route) — frontend calls without trailing slash
# and FastAPI 307 redirect causes issues with some HTTP clients
from reins.api.tasks_list import list_tasks
router.add_api_route("", list_tasks, methods=["GET"], tags=["tasks"])

router.include_router(tasks_list_router)
router.include_router(tasks_state_router)  # /statuses 必须在 /{task_id} 之前注册
router.include_router(tasks_labels_router)  # /labels/all 必须在 /{task_id} 之前注册
router.include_router(tasks_lifecycle_router)  # /{task_id}/pause|resume 必须在 /{task_id} 之前注册
router.include_router(tasks_review_router)  # /{task_id}/verify, /review, /verifier, /verifications
router.include_router(tasks_execution_router)  # /{task_id}/progress, /fail, /failure-log, /retry
router.include_router(tasks_crud_read_router)
router.include_router(tasks_crud_create_router)
router.include_router(tasks_crud_update_router)
router.include_router(tasks_crud_delete_router)

__all__ = ["router"]