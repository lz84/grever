"""
统一异常体系
================
从 nexus.common.exceptions 迁移过来（nexus 模块已废弃，2026-04-27）

用途：
  - Reins 工作流引擎异常
  - Grasp 认知异常
  - 数据库异常
  - 业务异常
"""

from enum import IntEnum
from typing import Optional, Dict, Any, Callable, TypeVar, List
import logging
import uuid
import re

logger = logging.getLogger(__name__)


# ============================================================
# P5-09-01: 错误码定义
# ============================================================

class ErrorCode(IntEnum):
    """
    统一错误码定义
    """

    # ==================== 通用错误 (1000-1999) ====================
    SUCCESS = 0  # 成功

    # 参数相关
    INVALID_PARAMS = 1001  # 参数无效
    MISSING_PARAMS = 1002  # 缺少必需参数
    PARAM_FORMAT_ERROR = 1003  # 参数格式错误

    # 业务相关
    BUSINESS_ERROR = 1004  # 业务错误
    OPERATION_NOT_ALLOWED = 1005  # 操作不允许
    RESOURCE_CONFLICT = 1006  # 资源冲突

    # 请求相关
    REQUEST_TOO_LARGE = 1007  # 请求过大
    REQUEST_TIMEOUT = 1008  # 请求超时
    METHOD_NOT_ALLOWED = 1009  # 方法不允许
    NOT_IMPLEMENTED = 1010  # 未实现

    # 资源相关
    NOT_FOUND = 1011  # 资源未找到

    # ==================== Grasp 认知错误 (2000-2999) ====================
    GRASP_INVALID_CONTENT = 2001  # 认知内容无效
    GRASP_POISON_DETECTED = 2002  # 检测到认知毒
    GRASP_LOW_QUALITY = 2003  # 认知质量过低
    GRASP_STORAGE_ERROR = 2004  # 认知存储错误
    GRASP_QUERY_ERROR = 2005  # 认知查询错误
    GRASP_INDEX_ERROR = 2006  # 认知索引错误
    GRASP_NOT_FOUND = 2007  # 认知不存在
    GRASP_FORBIDDEN = 2008  # 认知更新权限不足
    GRASP_INVALID_UPDATE = 2009  # 认知更新参数无效
    GRASP_BACKEND_UNAVAILABLE = 2010  # 认知后端不可用
    GRASP_INJECT_ERROR = 2011  # 认知注入失败
    GRASP_RETRIEVE_ERROR = 2012  # 认知检索失败
    GRASP_UPDATE_ERROR = 2013  # 认知更新失败
    GRASP_DELETE_ERROR = 2014  # 认知删除失败

    # ==================== Reins 任务错误 (3000-3999) ====================
    # 任务创建
    REINS_TASK_CREATE_FAILED = 3001  # 任务创建失败
    REINS_TASK_INVALID_CONFIG = 3002  # 任务配置无效
    REINS_TASK_NOT_FOUND = 3010  # 任务不存在

    # 任务执行
    REINS_EXECUTION_ERROR = 3003  # 任务执行错误
    REINS_AGENT_NOT_FOUND = 3004  # Agent 不存在
    REINS_AGENT_FAILED = 3005  # Agent 执行失败
    REINS_AGENT_OFFLINE = 3011  # Agent 离线

    # 任务状态
    REINS_INVALID_STATUS = 3006  # 无效的任务状态
    REINS_STATUS_CONFLICT = 3007  # 任务状态冲突
    REINS_INVALID_STATE_TRANSITION = 3012  # 无效的状态转换

    # 任务编排
    REINS_ORCHESTRATION_ERROR = 3008  # 编排错误
    REINS_CYCLE_DETECTED = 3009  # 检测到循环依赖

    # ==================== Evo 实验错误 (4000-4999) ====================
    EVO_EXPERIMENT_CREATE_FAILED = 4001  # 实验创建失败
    EVO_EXPERIMENT_NOT_FOUND = 4002  # 实验不存在
    EVO_EXECUTION_ERROR = 4003  # 实验执行错误
    EVO_RESULT_NOT_AVAILABLE = 4004  # 实验结果不可用
    EVO_COMPARISON_ERROR = 4005  # 实验对比错误

    # ==================== Reach 方案错误 (5000-5999) ====================
    REACH_SCHEME_CREATE_FAILED = 5001  # 方案创建失败
    REACH_SCHEME_NOT_FOUND = 5002  # 方案不存在
    REACH_DEPLOY_FAILED = 5003  # 方案部署失败
    REACH_DEPLOYMENT_ERROR = 5004  # 部署错误

    # ==================== Vigil 安全错误 (6000-6999) ====================
    # 认证
    VIGIL_AUTH_FAILED = 6001  # 认证失败
    VIGIL_TOKEN_INVALID = 6002  # Token 无效
    VIGIL_TOKEN_EXPIRED = 6003  # Token 过期

    # 授权
    VIGIL_AUTHORIZATION_FAILED = 6004  # 授权失败
    VIGIL_PERMISSION_DENIED = 6005  # 权限拒绝

    # 信任分
    VIGIL_TRUST_SCORE_TOO_LOW = 6006  # 信任分过低
    VIGIL_TRUST_SCORE_INVALID = 6007  # 信任分无效

    # 审计
    VIGIL_AUDIT_ERROR = 6008  # 审计错误

    # 异常检测
    VIGIL_ANOMALY_DETECTED = 6009  # 检测到异常
    VIGIL_ATTACK_DETECTED = 6010  # 检测到攻击

    # ==================== 数据库错误 (7000-7999) ====================
    DB_CONNECTION_ERROR = 7001  # 数据库连接错误
    DB_QUERY_ERROR = 7002  # 数据库查询错误
    DB_COMMIT_ERROR = 7003  # 数据库提交错误
    DB_POOL_EXHAUSTED = 7004  # 连接池耗尽
    DB_POOL_RECONNECT_FAILED = 7005  # 连接池重连失败

    # ==================== 网络错误 (8000-8999) ====================
    NETWORK_CONNECTION_ERROR = 8001  # 网络连接错误
    NETWORK_TIMEOUT = 8002  # 网络超时
    NETWORK_UNAVAILABLE = 8003  # 网络不可用

    # ==================== 系统错误 (9000-9999) ====================
    SYSTEM_ERROR = 9001  # 系统错误
    INTERNAL_ERROR = 9002  # 内部错误
    RATE_LIMIT_EXCEEDED = 9003  # 超出速率限制
    SERVICE_UNAVAILABLE = 9004  # 服务不可用


# ============================================================
# P5-09-01 + P5-09-05: 业务异常类
# ============================================================

class GreverException(Exception):
    """
    Grever 基础异常类
    所有 Grever 异常都继承自此类
    """

    def __init__(
        self,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        message: str = "Internal error",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.cause = cause
        self.reference_id = str(uuid.uuid4())[:8]

        # 构建异常消息
        exception_message = f"[{code.name}] {message}"
        if details:
            exception_message += f" {details}"

        super().__init__(exception_message)

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式，用于 API 响应
        统一格式: { "error": { "code", "message", "details"?, "reference_id" } }
        """
        result: Dict[str, Any] = {
            "error": {
                "code": int(self.code),
                "message": self.message,
                "reference_id": self.reference_id,
            }
        }

        if self.details:
            result["error"]["details"] = self.details

        if self.cause:
            result["error"]["cause"] = str(self.cause)

        return result

    @property
    def http_status(self) -> int:
        """
        P5-09-03: HTTP 状态码映射

        1000-4999 → 400 (客户端错误)
        5000-5999 → 403 (禁止)
        6001-6003 → 401 (未认证)
        6004-6999 → 403 (未授权)
        7000-7999 → 500 (服务器错误)
        8000-8999 → 503 (服务不可用)
        9000-9999 → 500 (服务器错误)
        """
        if self.code <= 0:
            return 200
        elif 1000 <= self.code < 5000:
            return 400
        elif 6001 <= self.code <= 6003:
            return 401
        elif 5000 <= self.code < 7000:
            return 403
        elif 7000 <= self.code < 8000:
            return 500
        elif 8000 <= self.code < 9000:
            return 503
        else:
            return 500


class BusinessException(GreverException):
    """业务异常 - 业务逻辑错误"""

    def __init__(
        self,
        message: str = "Business error",
        code: ErrorCode = ErrorCode.BUSINESS_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(code=code, message=message, details=details)


class ValidationException(GreverException):
    """参数验证异常"""

    def __init__(
        self,
        message: str = "Validation error",
        field: Optional[str] = None,
        value: Any = None,
    ):
        details: Dict[str, Any] = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value

        super().__init__(
            code=ErrorCode.INVALID_PARAMS,
            message=message,
            details=details,
        )


class AuthenticationException(GreverException):
    """认证异常"""

    def __init__(
        self,
        message: str = "Authentication failed",
        code: ErrorCode = ErrorCode.VIGIL_AUTH_FAILED,
    ):
        super().__init__(code=code, message=message)


class AuthorizationException(GreverException):
    """授权异常"""

    def __init__(
        self,
        message: str = "Authorization failed",
        code: ErrorCode = ErrorCode.VIGIL_PERMISSION_DENIED,
    ):
        super().__init__(code=code, message=message)


class NotFoundException(GreverException):
    """资源未找到异常"""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        details: Dict[str, Any] = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=message,
            details=details,
        )


class RateLimitException(GreverException):
    """速率限制异常"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
    ):
        details: Dict[str, Any] = {}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            details=details,
        )


class DatabaseException(GreverException):
    """数据库异常"""

    def __init__(
        self,
        message: str = "Database error",
        code: ErrorCode = ErrorCode.DB_QUERY_ERROR,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            cause=original_error,
        )


# ============================================================
# P5-09-05: 业务异常类 - Reins 领域
# ============================================================

class TaskNotFoundError(GreverException):
    """任务不存在"""

    def __init__(self, task_id: str):
        super().__init__(
            code=ErrorCode.REINS_TASK_NOT_FOUND,
            message=f"Task not found: {task_id}",
            details={"task_id": task_id},
        )


class AgentNotFoundError(GreverException):
    """Agent 不存在"""

    def __init__(self, agent_id: str):
        super().__init__(
            code=ErrorCode.REINS_AGENT_NOT_FOUND,
            message=f"Agent not found: {agent_id}",
            details={"agent_id": agent_id},
        )


class AgentOfflineError(GreverException):
    """Agent 离线"""

    def __init__(self, agent_id: str):
        super().__init__(
            code=ErrorCode.REINS_AGENT_OFFLINE,
            message=f"Agent is offline: {agent_id}",
            details={"agent_id": agent_id},
        )


class InvalidStateTransitionError(GreverException):
    """无效的状态转换"""

    def __init__(
        self,
        resource_type: str,
        current_state: str,
        requested_state: str,
        allowed_states: Optional[List[str]] = None,
    ):
        details: Dict[str, Any] = {
            "resource_type": resource_type,
            "current_state": current_state,
            "requested_state": requested_state,
        }
        if allowed_states is not None:
            details["allowed_states"] = allowed_states

        super().__init__(
            code=ErrorCode.REINS_INVALID_STATE_TRANSITION,
            message=f"无效的状态转换: {resource_type} 无法从 '{current_state}' 转换到 '{requested_state}'",
            details=details,
        )


class TaskStateConflictError(GreverException):
    """任务状态冲突"""

    def __init__(self, task_id: str, current_status: str):
        super().__init__(
            code=ErrorCode.REINS_STATUS_CONFLICT,
            message=f"Task status conflict",
            details={"task_id": task_id, "current_status": current_status},
        )


class GoalNotFoundError(GreverException):
    """Goal 不存在"""

    def __init__(self, goal_id: str):
        super().__init__(
            code=ErrorCode.REINS_TASK_NOT_FOUND,
            message=f"Goal not found: {goal_id}",
            details={"goal_id": goal_id},
        )


class WorkflowNotFoundError(GreverException):
    """Workflow 不存在"""

    def __init__(self, workflow_id: str):
        super().__init__(
            code=ErrorCode.REINS_TASK_NOT_FOUND,
            message=f"Workflow not found: {workflow_id}",
            details={"workflow_id": workflow_id},
        )


class CycleDetectedError(GreverException):
    """检测到循环依赖"""

    def __init__(self, cycle_nodes: Optional[List[str]] = None):
        details: Dict[str, Any] = {}
        if cycle_nodes:
            details["cycle_nodes"] = cycle_nodes

        super().__init__(
            code=ErrorCode.REINS_CYCLE_DETECTED,
            message="检测到循环依赖",
            details=details,
        )


# ============================================================
# Sensitive Information Masking
# ============================================================

_SENSITIVE_PATTERNS = [
    (r'password["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'password=***'),
    (r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'api_key=***'),
    (r'token["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'token=***'),
    (r'bearer\s+([a-zA-Z0-9_\-\.]+)', 'bearer ***'),
    (r'Authorization["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'Authorization=***'),
    (r'secret["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'secret=***'),
    (r'private[_-]?key["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'private_key=***'),
    (r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', '***@***'),
    (r'conn(?:ection)?_?string["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', 'conn_string=***'),
    (r'(?<=key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]{20,})', '***'),
]


def mask_sensitive_data(text: str) -> str:
    """
    Mask sensitive information in error messages.
    """
    if not text:
        return text
    result = text
    for pattern, replacement in _SENSITIVE_PATTERNS:
        try:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        except re.error:
            pass
    return result


def safe_error_message(error: Exception, include_details: bool = False) -> str:
    """
    Build a safe error message that won't leak sensitive data.
    """
    if include_details:
        raw = f"{type(error).__name__}: {str(error)}"
        masked = mask_sensitive_data(raw)
        return masked
    return f"{type(error).__name__} occurred. Please contact support with reference ID."


# ============================================================
# Exception Interceptor
# ============================================================

T = TypeVar("T")


class GreverErrorHandler:
    """
    Centralized exception interceptor.

    Features:
    - Catches all exceptions and converts to structured responses
    - Masks sensitive information automatically
    - Generates error reference IDs for support
    - Structured logging with error correlation
    - HTTP status code mapping
    """

    def __init__(self, include_details_in_logs: bool = True):
        self.include_details_in_logs = include_details_in_logs

    def handle_exception(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> GreverException:
        """
        Intercept an exception and convert to GreverException.
        """
        reference_id = str(uuid.uuid4())[:8]
        ctx = context or {}

        if isinstance(error, GreverException):
            safe_message = mask_sensitive_data(error.message)
            safe_details = {}
            for k, v in error.details.items():
                if isinstance(v, str):
                    safe_details[k] = mask_sensitive_data(v)
                else:
                    safe_details[k] = v

            error.message = safe_message
            error.details = safe_details
            error.reference_id = reference_id
            return error

        error_message = mask_sensitive_data(str(error))
        error_type = type(error).__name__

        logger.error(
            f"[{reference_id}] Unhandled {error_type}: {error_message}",
            extra={
                "reference_id": reference_id,
                "error_type": error_type,
                "context": ctx,
            },
            exc_info=self.include_details_in_logs,
        )

        code_map = {
            "TimeoutError": ErrorCode.REQUEST_TIMEOUT,
            "ConnectionError": ErrorCode.NETWORK_CONNECTION_ERROR,
            "ValueError": ErrorCode.INVALID_PARAMS,
            "KeyError": ErrorCode.INVALID_PARAMS,
            "PermissionError": ErrorCode.VIGIL_PERMISSION_DENIED,
            "AuthenticationError": ErrorCode.VIGIL_AUTH_FAILED,
        }

        code = code_map.get(error_type, ErrorCode.INTERNAL_ERROR)

        wrapped = GreverException(
            code=code,
            message=error_message if self.include_details_in_logs else f"{error_type} occurred",
            details={
                "reference_id": reference_id,
                "error_type": error_type,
                **{k: mask_sensitive_data(str(v)) if isinstance(v, str) else v for k, v in ctx.items()},
            },
            cause=error if self.include_details_in_logs else None,
        )
        wrapped.reference_id = reference_id
        return wrapped

    def to_dict(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Convert an exception to a structured dict suitable for API responses.
        """
        nex = self.handle_exception(error, context)
        result = nex.to_dict()
        result["error"]["reference_id"] = getattr(nex, "reference_id", None)
        return result

    def to_http_response(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> tuple:
        """
        Convert an exception to an HTTP response tuple.
        """
        nex = self.handle_exception(error, context)
        return nex.to_dict(), nex.http_status


def with_error_handling(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to wrap a function with centralized error handling.
    """
    handler = GreverErrorHandler()

    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            nex = handler.handle_exception(e, {"function": func.__name__})
            raise nex

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def with_safe_error_handling(
    func: Callable[..., T],
    default_return: Any = None,
    context: Optional[Dict[str, Any]] = None,
) -> Callable[..., T]:
    """
    Decorator that catches exceptions and returns a safe error response
    instead of raising.

    Usage:
        @with_safe_error_handling(default_return={"error": "failed"})
        def my_function(arg1, arg2):
            ...
    """
    handler = GreverErrorHandler()

    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ctx = {"function": func.__name__, **(context or {})}
            nex = handler.handle_exception(e, ctx)
            logger.warning(
                f"[{getattr(nex, 'reference_id', 'N/A')}] {func.__name__} failed: {nex.message}"
            )
            return default_return

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper
