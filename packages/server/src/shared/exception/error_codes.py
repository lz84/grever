"""
P5-09 错误码定义

定义统一错误码枚举：
- 1001-1999: 参数错误（INVALID_PARAMETER, MISSING_FIELD, INVALID_STATE）
- 2001-2999: 业务错误（INVALID_STATE_TRANSITION, AGENT_OFFLINE, TASK_NOT_FOUND, GOAL_NOT_FOUND）
- 3001-3999: 系统错误（INTERNAL_ERROR, DB_ERROR, EVENT_PUBLISH_FAILED）
"""

from enum import IntEnum
from typing import Dict


class ErrorCode(IntEnum):
    """
    统一错误码定义（P5-09-01）

    错误码范围：
    - 1001-1999: 参数错误
    - 2001-2999: 业务错误
    - 3001-3999: 系统错误
    """

    # ==================== 参数错误 (1001-1999) ====================
    INVALID_PARAMETER = 1001      # 参数无效
    MISSING_FIELD = 1002          # 缺少必需字段
    INVALID_STATE = 1003           # 参数状态无效

    # ==================== 业务错误 (2001-2999) ====================
    INVALID_STATE_TRANSITION = 2001  # 非法状态转换（P5-03-02）
    AGENT_OFFLINE = 2002            # Agent 不在线
    TASK_NOT_FOUND = 2003           # 任务不存在
    GOAL_NOT_FOUND = 2004           # 目标不存在
    PROJECT_NOT_FOUND = 2005        # 项目不存在
    WORKFLOW_NOT_FOUND = 2006       # 工作流不存在
    DISPUTE_NOT_FOUND = 2007        # 争议不存在
    TASK_BLOCKED = 2008             # 任务被阻塞（P5-03-06）
    AGENT_NOT_FOUND = 2009          # Agent 不存在
    RESOURCE_CONFLICT = 2010        # 资源冲突
    DUPLICATE_ENTRY = 2011          # 重复条目

    # ==================== 系统错误 (3001-3999) ====================
    INTERNAL_ERROR = 3001           # 内部错误
    DB_ERROR = 3002                 # 数据库错误
    EVENT_PUBLISH_FAILED = 3003      # 事件发布失败（P5-01）
    ADAPTER_NOT_AVAILABLE = 3004    # Adapter 不可用

    @property
    def http_status(self) -> int:
        """
        获取对应的 HTTP 状态码（P5-09-03）
        """
        if 1001 <= self.value < 2000:
            return 400  # Bad Request
        elif 2001 <= self.value < 3000:
            if self.value in (2003, 2004, 2005, 2006, 2007, 2009):
                return 404  # Not Found
            return 400  # Business error → Bad Request
        elif 3001 <= self.value < 4000:
            return 500  # Internal Server Error
        return 500

    @property
    def error_type(self) -> str:
        """获取错误类型名称"""
        return self.name.lower()

    def to_dict(self) -> Dict[str, any]:
        """转换为字典"""
        return {
            "code": self.value,
            "name": self.name,
            "type": self.error_type,
            "http_status": self.http_status,
        }
