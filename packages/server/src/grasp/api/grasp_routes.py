"""Grasp API 路由 — FastAPI endpoints for GraspFacade（统一异常包装）"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from grasp.facade.service import GraspFacade, UnknownBackendError
from grasp.facade.schemas import (
    CognitionInjectRequest, CognitionInjectResponse,
    CognitionRetrieveRequest, CognitionRetrieveResponse,
    CognitionItemResponse, CognitionUpdateRequest,
    BackendStatusResponse, SwitchBackendRequest,
)
from grasp.facade.models import CognitionInput
from shared.common.exceptions import GreverException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/grasp", tags=["grasp"])

# 全局 facade 实例（懒加载）
_facade: Optional[GraspFacade] = None


def get_facade() -> GraspFacade:
    global _facade
    if _facade is None:
        _facade = GraspFacade()
    return _facade


def _facade_error_response(e: Exception, operation: str) -> JSONResponse:
    """
    将 facade 层异常转换为标准 JSON 响应。
    - GreverException：已统一包装，直接提取错误信息
    - 其他异常：fallback，不泄露内部细节

    直接返回 JSONResponse 而非 HTTPException，避免被全局异常处理器二次转换。
    """
    if isinstance(e, GreverException):
        # GreverException 已包含 ErrorCode、message、details
        # 不暴露内部异常类型名或 traceback
        return JSONResponse(
            status_code=e.http_status,
            content=e.to_dict(),
        )
    # 未知异常 → 通用 500，不泄露内部细节
    logger.error(f"[GraspAPI] {operation} 发生未预期异常: {type(e).__name__}: {e}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 9002,
                "message": f"{operation} 发生内部错误",
            }
        },
    )


@router.post("/inject", response_model=CognitionInjectResponse)
async def inject_cognition(req: CognitionInjectRequest):
    """注入认知到知识库"""
    facade = get_facade()
    try:
        input_data = CognitionInput(
            content=req.content,
            type=req.type.value,
            tags=req.tags,
            confidence=req.confidence,
            metadata=req.metadata,
            domain=req.domain,
        )
        result = await facade.inject(input_data)
        return CognitionInjectResponse(
            cognition_id=result.cognition_id,
            status="success",
            quality_score=result.quality_score,
            is_duplicate=result.is_duplicate,
        )
    except Exception as e:
        return _facade_error_response(e, "inject")


@router.post("/retrieve", response_model=CognitionRetrieveResponse)
async def retrieve_cognition(req: CognitionRetrieveRequest):
    """检索认知"""
    facade = get_facade()
    try:
        type_filters = [t.value for t in req.type] if req.type else None
        result = await facade.retrieve(
            query=req.query,
            mode=req.mode,
            limit=req.limit,
            offset=req.offset,
            type=type_filters,
            tags=req.tags,
            min_confidence=req.min_confidence,
            domain=req.domain,
        )
        items = [
            CognitionItemResponse(
                cognition_id=item.cognition_id,
                type=item.type,
                content=item.content,
                tags=item.tags,
                confidence=item.confidence,
                quality_score=item.quality_score,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in result.items
        ]
        return CognitionRetrieveResponse(
            items=items,
            total=result.total,
            has_more=result.has_more,
        )
    except Exception as e:
        return _facade_error_response(e, "retrieve")


@router.post("/update/{cognition_id}")
async def update_cognition(cognition_id: str, req: CognitionUpdateRequest):
    """更新认知"""
    facade = get_facade()
    try:
        result = await facade.update(
            cognition_id=cognition_id,
            content=req.content,
            metadata=req.metadata,
        )
        return {
            "cognition_id": result.cognition_id,
            "status": "updated",
            "quality_score": result.quality_score,
        }
    except Exception as e:
        return _facade_error_response(e, "update")


@router.delete("/{cognition_id}")
async def delete_cognition(cognition_id: str):
    """删除认知"""
    facade = get_facade()
    try:
        success = await facade.delete(cognition_id=cognition_id)
        if not success:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": 2007,
                        "message": f"Cognition '{cognition_id}' not found",
                    }
                },
            )
        return {"cognition_id": cognition_id, "status": "deleted"}
    except Exception as e:
        return _facade_error_response(e, "delete")


@router.get("/backends")
async def list_backends():
    """列出所有后端及其状态"""
    facade = get_facade()
    return facade.list_backends()


@router.get("/active-backend")
async def get_active_backend():
    """获取当前活跃后端"""
    facade = get_facade()
    return {"active_backend": facade.get_active_backend()}


@router.post("/switch-backend")
async def switch_backend(req: SwitchBackendRequest):
    """切换活跃后端"""
    facade = get_facade()
    try:
        await facade.switch_backend(req.backend_name)
        return {"active_backend": facade.get_active_backend(), "status": "switched"}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        return _facade_error_response(e, "switch-backend")
