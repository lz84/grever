"""
Attachments Router - Facade 聚合
"""

from fastapi import APIRouter

from .attachments import router as attachments_router

router = APIRouter(prefix="/api/v1", tags=["attachments"])

router.include_router(attachments_router)
