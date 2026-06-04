"""
统一异常处理器 (P5-09-04, P5-09-05)

提供 FastAPI/Flask 等框架的异常处理中间件。
所有未捕获异常统一格式化返回，不泄露内部堆栈。

统一错误响应格式（P5-09-02）：
{
    "code": 1001,           # 错误码
    "message": "参数无效",   # 用户友好的错误消息
    "details": {...},       # 详细信息（可选）
    "error_type": "invalid_parameter"  # 错误类型（可选）
}
"""

import logging
import traceback
from typing import Tuple, Dict, Any, Optional

from shared.exception.error_codes import ErrorCode
from shared.exception.error_response import ErrorResponse, APIError

logger = logging.getLogger(__name__)

# Backward compat: NexusException was planned at nexus.common.exceptions
# but lives at exception.exceptions
try:
    from shared.exception.exceptions import NexusException
except ImportError:
    NexusException = None  # type: ignore


def format_exception_details(exc: Exception) -> Dict[str, Any]:
    """
    格式化异常详细信息（仅用于开发/调试环境）
    """
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
    }


def create_error_response(
    exc_or_code: Any,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    include_traceback: bool = False,
) -> Tuple[int, Dict[str, Any]]:
    """
    创建错误响应（P5-09-02）

    支持两种调用方式：
    1. create_error_response(exc: NexusException) - 使用 exc.http_status
    2. create_error_response(ErrorCode.INVALID_PARAMETER, message="...", details={...})

    :param exc_or_code: NexusException 实例或 ErrorCode 枚举
    :param message: 自定义消息（可选）
    :param details: 详细信息（可选）
    :param include_traceback: 是否包含堆栈跟踪（开发环境）
    :return: (HTTP 状态码，响应体)
    """
    # 判断调用方式
    if isinstance(exc_or_code, ErrorCode):
        error_response = ErrorResponse.from_error_code(
            exc_or_code,
            message=message,
            details=details,
        )
    elif NexusException and isinstance(exc_or_code, NexusException):
        # 来自 nexus.common.exceptions 的 NexusException
        # 使用其自身的 http_status 属性
        exc = exc_or_code
        body = exc.to_dict()
        if message:
            body["error"]["message"] = message
        if details:
            body["error"]["details"] = details
        if include_traceback and exc.cause:
            body["debug"] = format_exception_details(exc.cause)
        return exc.http_status, body
    elif hasattr(exc_or_code, 'code') and hasattr(exc_or_code, 'http_status'):
        # 兼容任何有 http_status 的异常
        exc = exc_or_code
        body = getattr(exc, 'to_dict', lambda: {"error": {"code": exc.code, "message": str(exc)}})()
        if message:
            body.setdefault("error", {})["message"] = message
        if details:
            body.setdefault("error", {})["details"] = details
        return exc.http_status, body
    else:
        # 兜底：通用内部错误
        error_response = ErrorResponse(
            code=ErrorCode.INTERNAL_ERROR.value,
            message=str(exc_or_code) if exc_or_code else "Unknown error",
        )
        return error_response.http_status, error_response.to_dict()

    result = error_response.to_dict()

    if include_traceback and isinstance(exc_or_code, Exception) and getattr(exc_or_code, 'cause', None):
        result["debug"] = format_exception_details(exc_or_code.cause)

    logger.error(
        f"Error occurred: code={error_response.code}, message={error_response.message}",
        extra={
            "error_code": error_response.code,
            "error_message": error_response.message,
            "error_details": error_response.details,
        },
        exc_info=isinstance(exc_or_code, Exception) and getattr(exc_or_code, 'cause', None) is not None,
    )

    return error_response.http_status, result


# ============================================================
# P5-09-04: FastAPI 全局异常处理器注册
# ============================================================

def register_fastapi_exception_handlers(app) -> None:
    """
    在 FastAPI 应用上注册全局异常处理器。

    使用方式:
    ```python
    from fastapi import FastAPI
    from shared.exception.handlers import register_fastapi_exception_handlers

    app = FastAPI()
    register_fastapi_exception_handlers(app)
    ```

    注册的处理器:
    1. NexusException → 结构化错误响应
    2. ValueError → 400 参数错误
    3. Exception → 捕获所有未预期异常，返回通用 500
    """
    from fastapi import Request, HTTPException
    from fastapi.responses import JSONResponse

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # FastAPI 内置 HTTPException → 统一格式
        error_response = ErrorResponse(
            code=ErrorCode.INVALID_STATE.value if exc.status_code == 400
            else ErrorCode.TASK_NOT_FOUND.value if exc.status_code == 404
            else ErrorCode.INTERNAL_ERROR.value,
            message=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.to_dict(),
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        # 参数验证错误
        status_code, body = create_error_response(
            ErrorCode.INVALID_PARAMETER,
            message=str(exc),
        )
        return JSONResponse(status_code=status_code, content=body)

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        # 未预期的异常 - 不泄露内部细节
        logger.exception(f"Unexpected error: {str(exc)}")

        error_response = ErrorResponse(
            code=ErrorCode.INTERNAL_ERROR.value,
            message="Internal server error",
        )

        return JSONResponse(
            status_code=500,
            content=error_response.to_dict(),
        )


# ============================================================
# P5-09-05: 业务异常类
# ============================================================

class TaskNotFoundError(Exception):
    """任务不存在异常（P5-09-05）"""
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.code = ErrorCode.TASK_NOT_FOUND
        super().__init__(f"Task not found: {task_id}")

    def to_error_response(self) -> ErrorResponse:
        return APIError.task_not_found(self.task_id)


class GoalNotFoundError(Exception):
    """目标不存在异常（P5-09-05）"""
    def __init__(self, goal_id: str):
        self.goal_id = goal_id
        self.code = ErrorCode.GOAL_NOT_FOUND
        super().__init__(f"Goal not found: {goal_id}")

    def to_error_response(self) -> ErrorResponse:
        return APIError.goal_not_found(self.goal_id)


class AgentOfflineError(Exception):
    """Agent 不在线异常（P5-09-05）"""
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.code = ErrorCode.AGENT_OFFLINE
        super().__init__(f"Agent offline: {agent_id}")

    def to_error_response(self) -> ErrorResponse:
        return APIError.agent_offline(self.agent_id)


class InvalidStateTransitionError(Exception):
    """非法状态转换异常（P5-09-05, P5-03-02）"""
    def __init__(self, from_state: str, to_state: str, allowed: list = None):
        self.from_state = from_state
        self.to_state = to_state
        self.allowed = allowed or []
        self.code = ErrorCode.INVALID_STATE_TRANSITION
        super().__init__(f"Invalid state transition: {from_state} → {to_state}")

    def to_error_response(self) -> ErrorResponse:
        return APIError.invalid_state_transition(
            self.from_state,
            self.to_state,
            self.allowed,
        )


# Flask 异常处理器
def flask_exception_handler(app):
    """
    Flask 异常处理器工厂
    """
    from flask import Flask, jsonify

    if not isinstance(app, Flask):
        raise TypeError("app must be a Flask instance")

    @app.errorhandler(Exception)
    def handle_general_exception(exc: Exception):
        logger.exception("Unexpected error occurred")

        error_response = ErrorResponse(
            code=ErrorCode.INTERNAL_ERROR.value,
            message="Internal server error",
        )

        return jsonify(error_response.to_dict()), 500

    return None


# 通用装饰器：包裹函数并处理异常
def handle_exceptions(func):
    """
    异常处理装饰器

    使用方式:
    ```python
    @handle_exceptions
    def my_function(param):
        # 业务逻辑
        pass
    ```
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (NexusException, Exception) if NexusException else Exception:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}")
            if NexusException:
                raise NexusException(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"Unexpected error in {func.__name__}: {str(e)}",
                    cause=e,
                )
            raise

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


# 异步异常处理装饰器
async def async_handle_exceptions(func):
    """
    异步异常处理装饰器
    """
    import asyncio

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (NexusException, Exception) if NexusException else Exception:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}")
            if NexusException:
                raise NexusException(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"Unexpected error in {func.__name__}: {str(e)}",
                    cause=e,
                )
            raise

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper
