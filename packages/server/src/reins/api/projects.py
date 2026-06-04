"""
项目管理 API — Facade

子模块:
  - projects_list: 列表与 debug 端点
  - projects_crud: GET/POST/PUT/DELETE
  - projects_diagram: 流程图端点（简化版）
  - projects_workflow: 工作流端点（diagram/task-tree/status）
  - projects_verifier_lifecycle: 验证器/暂停/恢复
"""
from fastapi import APIRouter

from .projects_list import router as list_router
from .projects_crud import router as crud_router
from .projects_workflow import router as workflow_router
from .projects_verifier_lifecycle import router as verifier_router

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

# Sprint 104: Register list endpoint without trailing slash (frontend calls without /)
# FastAPI 307 redirect causes issues with some HTTP clients
from .projects_list import list_projects
router.add_api_route("", list_projects, methods=["GET"], tags=["projects"])

router.include_router(list_router)
router.include_router(crud_router)
router.include_router(workflow_router)
router.include_router(verifier_router)
