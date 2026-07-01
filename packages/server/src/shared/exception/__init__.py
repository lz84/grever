"""
Grever 统一异常处理模块
提供全局异常框架和错误码定义

P5-09 新增：
- error_codes: ErrorCode 枚举（1001-3999）
- error_response: ErrorResponse 统一错误响应格式
- handlers: FastAPI 全局异常处理器
"""

# 原有异常（从 exception.exceptions）
from .exceptions import (
    GreverException,
    BusinessException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    RateLimitException,
    DatabaseException,
    ErrorCode,
)

# P5-09 新增：业务异常类
from .handlers import (
    TaskNotFoundError,
    GoalNotFoundError,
    AgentOfflineError,
    InvalidStateTransitionError,
)

# P5-09 新增：错误码和响应格式
from .error_codes import ErrorCode as GreverErrorCode
from .error_response import ErrorResponse, APIError

__all__ = [
    # 原有异常
    'GreverException',
    'BusinessException',
    'ValidationException',
    'AuthenticationException',
    'AuthorizationException',
    'NotFoundException',
    'RateLimitException',
    'DatabaseException',
    'ErrorCode',
    # P5-09 业务异常
    'TaskNotFoundError',
    'GoalNotFoundError',
    'AgentOfflineError',
    'InvalidStateTransitionError',
    # P5-09 新增
    'GreverErrorCode',
    'ErrorResponse',
    'APIError',
]
