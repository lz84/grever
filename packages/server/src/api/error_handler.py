"""
Nexus 全局异常处理器

所有 API 错误通过这里统一返回格式：

{
    "error": "ERROR_CODE",
    "message": "中文消息",
    "details": {...}
}
"""

from loguru import logger
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.error_codes import (
    NexusErrorCode,
    ERROR_CODE_TO_STATUS,
    ERROR_CODE_TO_MESSAGE,
)

def make_error_response(
    error_code: NexusErrorCode,
    message: str = None,
    details: dict = None,
    http_status: int = None,
) -> dict:
    """构建统一错误响应"""
    return {
        "error": error_code.value,
        "message": message or ERROR_CODE_TO_MESSAGE.get(error_code, "未知错误"),
        "details": details or {},
    }

async def nexus_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理 HTTPException，转换为统一格式"""
    detail = exc.detail
    if isinstance(detail, dict):
        # 已经是统一格式
        return JSONResponse(status_code=exc.status_code, content=detail)
    elif isinstance(detail, str) and detail.startswith("{"):
        # JSON 字符串
        import json
        try:
            content = json.loads(detail)
            return JSONResponse(status_code=exc.status_code, content=content)
        except Exception:
            pass
    
    # 通用 HTTPException → 根据状态码推断错误码
    status_to_code = {v: k for k, v in ERROR_CODE_TO_STATUS.items()}
    error_code = status_to_code.get(exc.status_code, NexusErrorCode.INTERNAL_ERROR)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=make_error_response(error_code, str(detail)),
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """处理请求参数校验错误"""
    errors = []
    for err in exc.errors():
        loc = ".".join(str(l) for l in err["loc"])
        errors.append({"field": loc, "message": err["msg"], "type": err["type"]})
    
    content = make_error_response(
        NexusErrorCode.VALIDATION_ERROR,
        message="参数校验失败",
        details={"validation_errors": errors},
    )
    return JSONResponse(status_code=400, content=content)

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理所有未捕获的异常"""
    # 增强详情：包含错误类型和消息
    exc_details = {"exception": type(exc).__name__}
    if hasattr(exc, 'errors'):
        exc_details["validation_errors"] = exc.errors()
    if hasattr(exc, 'body'):
        exc_details["body"] = str(exc.body)[:200]
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=make_error_response(
            NexusErrorCode.INTERNAL_ERROR,
            message="服务器内部错误",
            details=exc_details,
        ),
    )

def register_exception_handlers(app: FastAPI):
    """注册全局异常处理器"""
    app.add_exception_handler(HTTPException, nexus_http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, nexus_http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
