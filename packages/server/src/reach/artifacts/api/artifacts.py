"""
成果物共享 API — Facade

Sprint 28: Artifact 上传/下载
子模块:
  - artifacts_models: Pydantic 请求/响应模型
  - artifacts_helpers: 辅助函数
  - artifacts_create_list: 创建与列表端点
  - artifacts_get_download: 获取与下载端点
  - artifacts_update_delete: 更新与删除端点
"""
from fastapi import APIRouter

from .artifacts_create_list import router as create_list_router
from .artifacts_get_download import router as get_download_router
from .artifacts_update_delete import router as update_delete_router

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])
router.include_router(create_list_router)
router.include_router(get_download_router)
router.include_router(update_delete_router)
