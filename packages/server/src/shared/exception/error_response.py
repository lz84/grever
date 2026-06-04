"""
统一错误响应格式（P5-09-02, P5-09-03）

统一格式：
{
    "code": 1001,                    # 错误码
    "message": "参数无效",            # 用户友好的错误消息
    "details": {...},               # 详细信息（可选）
    "error_type": "invalid_parameter" # 错误类型（可选）
}

HTTP 状态码映射（P5-09-03）：
- 400: 参数错误、业务逻辑错误
- 401: 未认证
- 403: 权限不足
- 404: 资源不存在
- 500: 系统内部错误
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional
from shared.exception.error_codes import ErrorCode


@dataclass
class ErrorResponse:
    """
    统一错误响应格式（P5-09-02）

    格式：
    - code: 错误码（整数）
    - message: 用户友好的错误消息
    - details: 详细信息（可选，dict）
    - error_type: 错误类型（可选，字符串）
    """

    code: int
    message: str
    details: Optional[Dict[str, Any]] = None
    error_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于 API 响应）"""
        result = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        if self.error_type:
            result["error_type"] = self.error_type
        return result

    def to_http_response(self) -> tuple[int, Dict[str, Any]]:
        """转换为 HTTP 响应格式 (status_code, body)"""
        return self.http_status, self.to_dict()

    @property
    def http_status(self) -> int:
        """获取 HTTP 状态码"""
        try:
            error_code = ErrorCode(self.code)
            return error_code.http_status
        except (ValueError, TypeError):
            if 1001 <= self.code < 2000:
                return 400
            elif 2001 <= self.code < 3000:
                return 400
            return 500

    @classmethod
    def from_error_code(
        cls,
        error_code: ErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> "ErrorResponse":
        """
        从 ErrorCode 创建 ErrorResponse

        Args:
            error_code: 错误码枚举
            message: 自定义消息（可选，默认使用错误码默认消息）
            details: 详细信息（可选）
        """
        if message is None:
            message = cls._get_default_message(error_code)
        return cls(
            code=error_code.value,
            message=message,
            details=details,
            error_type=error_code.error_type,
        )

    @staticmethod
    def _get_default_message(error_code: ErrorCode) -> str:
        """获取错误码的默认消息"""
        messages = {
            ErrorCode.INVALID_PARAMETER: "参数无效",
            ErrorCode.MISSING_FIELD: "缺少必需字段",
            ErrorCode.INVALID_STATE: "状态无效",
            ErrorCode.INVALID_STATE_TRANSITION: "非法状态转换",
            ErrorCode.AGENT_OFFLINE: "Agent 不在线",
            ErrorCode.TASK_NOT_FOUND: "任务不存在",
            ErrorCode.GOAL_NOT_FOUND: "目标不存在",
            ErrorCode.PROJECT_NOT_FOUND: "项目不存在",
            ErrorCode.WORKFLOW_NOT_FOUND: "工作流不存在",
            ErrorCode.DISPUTE_NOT_FOUND: "争议不存在",
            ErrorCode.TASK_BLOCKED: "任务被阻塞",
            ErrorCode.AGENT_NOT_FOUND: "Agent 不存在",
            ErrorCode.RESOURCE_CONFLICT: "资源冲突",
            ErrorCode.DUPLICATE_ENTRY: "重复条目",
            ErrorCode.INTERNAL_ERROR: "内部错误",
            ErrorCode.DB_ERROR: "数据库错误",
            ErrorCode.EVENT_PUBLISH_FAILED: "事件发布失败",
            ErrorCode.ADAPTER_NOT_AVAILABLE: "适配器不可用",
        }
        return messages.get(error_code, "未知错误")


@dataclass
class APIError:
    """
    API 错误构造器（P5-09-02）

    提供便捷的错误创建方法。
    """

    @staticmethod
    def invalid_parameter(field: str, reason: str = "") -> ErrorResponse:
        """参数无效错误"""
        details = {"field": field}
        if reason:
            details["reason"] = reason
        return ErrorResponse.from_error_code(
            ErrorCode.INVALID_PARAMETER,
            message=f"参数 {field} 无效",
            details=details,
        )

    @staticmethod
    def missing_field(field: str) -> ErrorResponse:
        """缺少必需字段"""
        return ErrorResponse.from_error_code(
            ErrorCode.MISSING_FIELD,
            message=f"缺少必需字段: {field}",
            details={"field": field},
        )

    @staticmethod
    def invalid_state(state: str, reason: str = "") -> ErrorResponse:
        """状态无效"""
        details = {"state": state}
        if reason:
            details["reason"] = reason
        return ErrorResponse.from_error_code(
            ErrorCode.INVALID_STATE,
            message=f"状态 {state} 无效",
            details=details,
        )

    @staticmethod
    def task_not_found(task_id: str) -> ErrorResponse:
        """任务不存在"""
        return ErrorResponse.from_error_code(
            ErrorCode.TASK_NOT_FOUND,
            message=f"任务不存在: {task_id}",
            details={"task_id": task_id},
        )

    @staticmethod
    def goal_not_found(goal_id: str) -> ErrorResponse:
        """目标不存在"""
        return ErrorResponse.from_error_code(
            ErrorCode.GOAL_NOT_FOUND,
            message=f"目标不存在: {goal_id}",
            details={"goal_id": goal_id},
        )

    @staticmethod
    def invalid_state_transition(
        from_state: str,
        to_state: str,
        allowed: list = None,
    ) -> ErrorResponse:
        """非法状态转换（P5-03-02）"""
        details = {
            "from_state": from_state,
            "to_state": to_state,
        }
        if allowed:
            details["allowed_transitions"] = allowed
        return ErrorResponse.from_error_code(
            ErrorCode.INVALID_STATE_TRANSITION,
            message=f"非法状态转换: {from_state} → {to_state}",
            details=details,
        )

    @staticmethod
    def agent_offline(agent_id: str) -> ErrorResponse:
        """Agent 不在线"""
        return ErrorResponse.from_error_code(
            ErrorCode.AGENT_OFFLINE,
            message=f"Agent 不在线: {agent_id}",
            details={"agent_id": agent_id},
        )

    @staticmethod
    def internal_error(reason: str = "") -> ErrorResponse:
        """内部错误"""
        details = {}
        if reason:
            details["reason"] = reason
        return ErrorResponse.from_error_code(
            ErrorCode.INTERNAL_ERROR,
            message="内部错误",
            details=details if details else None,
        )

    @staticmethod
    def db_error(operation: str, reason: str = "") -> ErrorResponse:
        """数据库错误"""
        details = {"operation": operation}
        if reason:
            details["reason"] = reason
        return ErrorResponse.from_error_code(
            ErrorCode.DB_ERROR,
            message=f"数据库操作失败: {operation}",
            details=details,
        )
