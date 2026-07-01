"""
Grever 统一异常定义
包含基础异常类和错误码定义
"""

from enum import IntEnum
from typing import Optional, Dict, Any


class ErrorCode(IntEnum):
    """
    统一错误码定义
    
    错误码范围：
    - 0: 成功
    - 1000 - 1999: 通用错误
    - 2000 - 2999: Grasp 认知错误
    - 3000 - 3999: Reins 任务错误
    - 4000 - 4999: Evo 实验错误
    - 5000 - 5999: Reach 方案错误
    - 6000 - 6999: Vigil 安全错误
    - 7000 - 7999: 数据库错误
    - 8000 - 8999: 网络错误
    - 9000 - 9999: 系统错误
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
    
    # ==================== Grasp 认知错误 (2000-2999) ====================
    # 认知操作
    GRASP_INVALID_CONTENT = 2001  # 认知内容无效
    GRASP_POISON_DETECTED = 2002  # 检测到认知毒
    GRASP_LOW_QUALITY = 2003  # 认知质量过低
    GRASP_STORAGE_ERROR = 2004  # 认知存储错误
    
    # 认知检索
    GRASP_QUERY_ERROR = 2005  # 认知查询错误
    GRASP_INDEX_ERROR = 2006  # 认知索引错误
    
    # 认知更新
    GRASP_NOT_FOUND = 2007  # 认知不存在
    GRASP_FORBIDDEN = 2008  # 认知更新权限不足
    GRASP_INVALID_UPDATE = 2009  # 认知更新参数无效
    
    # ==================== Reins 任务错误 (3000-3999) ====================
    # 任务创建
    REINS_TASK_CREATE_FAILED = 3001  # 任务创建失败
    REINS_TASK_INVALID_CONFIG = 3002  # 任务配置无效
    
    # 任务执行
    REINS_EXECUTION_ERROR = 3003  # 任务执行错误
    REINS_AGENT_NOT_FOUND = 3004  # Agent 不存在
    REINS_AGENT_FAILED = 3005  # Agent 执行失败
    
    # 任务状态
    REINS_INVALID_STATUS = 3006  # 无效的任务状态
    REINS_STATUS_CONFLICT = 3007  # 任务状态冲突
    
    # 任务编排
    REINS_ORCHESTRATION_ERROR = 3008  # 编排错误
    REINS_CYCLE_DETECTED = 3009  # 检测到循环依赖
    
    # ==================== Evo 实验错误 (4000-4999) ====================
    # 实验管理
    EVO_EXPERIMENT_CREATE_FAILED = 4001  # 实验创建失败
    EVO_EXPERIMENT_NOT_FOUND = 4002  # 实验不存在
    
    # 实验执行
    EVO_EXECUTION_ERROR = 4003  # 实验执行错误
    EVO_RESULT_NOT_AVAILABLE = 4004  # 实验结果不可用
    
    # 实验对比
    EVO_COMPARISON_ERROR = 4005  # 实验对比错误
    
    # ==================== Reach 方案错误 (5000-5999) ====================
    # 方案管理
    REACH_SCHEME_CREATE_FAILED = 5001  # 方案创建失败
    REACH_SCHEME_NOT_FOUND = 5002  # 方案不存在
    
    # 方案部署
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
        
        # 构建异常消息
        exception_message = f"[{code.name}] {message}"
        if details:
            exception_message += f" {details}"
        
        super().__init__(exception_message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式，用于 API 响应
        """
        result = {
            "error": {
                "code": self.code,
                "message": self.message,
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
        获取对应的 HTTP 状态码
        """
        if self.code <= 0:
            return 200
        elif 1000 <= self.code < 3000:
            return 400  # Bad Request
        elif 3000 <= self.code < 5000:
            return 404  # Not Found
        elif 5000 <= self.code < 7000:
            return 403  # Forbidden
        elif 7000 <= self.code < 8000:
            return 500  # Internal Server Error
        elif 8000 <= self.code < 9000:
            return 503  # Service Unavailable
        else:
            return 500  # Internal Server Error


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
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
        
        super().__init__(
            code=ErrorCode.INVALID_PARAMS,
            message=message,
            details=details
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
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=message,
            details=details
        )


class RateLimitException(GreverException):
    """速率限制异常"""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
    ):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        
        super().__init__(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            details=details
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
            cause=original_error
        )
