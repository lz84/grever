"""
Grever 错误码定义

所有 API 错误必须使用这里定义的错误码，
禁止在代码中直接返回字符串错误信息。
"""

from enum import Enum

class GreverErrorCode(str, Enum):
    """Grever 系统错误码"""

    # ========== 通用错误（1xxx）==========
    INTERNAL_ERROR = "INTERNAL_ERROR"              # 内部错误
    VALIDATION_ERROR = "VALIDATION_ERROR"         # 参数校验失败
    NOT_FOUND = "NOT_FOUND"                        # 资源不存在
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"           # 重复条目
    INVALID_STATE = "INVALID_STATE"               # 状态不合法

    # ========== Task 错误（2xxx）==========
    TASK_NOT_FOUND = "TASK_NOT_FOUND"              # 任务不存在
    TASK_IN_INVALID_STATE = "TASK_IN_INVALID_STATE"  # 任务状态不合法（无法转换）
    ACCEPTANCE_CRITERIA_REQUIRED = "ACCEPTANCE_CRITERIA_REQUIRED"  # 必须设置验收标准
    TASK_NOT_ASSIGNABLE = "TASK_NOT_ASSIGNABLE"    # 任务不可分配
    TASK_BLOCKED_BY_DEPENDENCIES = "TASK_BLOCKED_BY_DEPENDENCIES"  # 任务被依赖阻塞
    TASK_RETRY_EXHAUSTED = "TASK_RETRY_EXHAUSTED"  # 重试次数耗尽
    TASK_TIMEOUT = "TASK_TIMEOUT"                  # 任务超时

    # ========== Goal 错误（3xxx）==========
    GOAL_NOT_FOUND = "GOAL_NOT_FOUND"              # 目标不存在
    GOAL_IN_INVALID_STATE = "GOAL_IN_INVALID_STATE"  # 目标状态不合法

    # ========== Project 错误（4xxx）==========
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"         # 项目不存在
    PROJECT_IN_INVALID_STATE = "PROJECT_IN_INVALID_STATE"  # 项目状态不合法

    # ========== Agent 错误（5xxx）==========
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"            # Agent 不存在
    AGENT_OFFLINE = "AGENT_OFFLINE"               # Agent 已离线
    AGENT_CAPACITY_FULL = "AGENT_CAPACITY_FULL"   # Agent 容量已满

    # ========== Workflow 错误（6xxx）==========
    WORKFLOW_NOT_FOUND = "WORKFLOW_NOT_FOUND"       # 工作流不存在
    WORKFLOW_STEP_NOT_FOUND = "WORKFLOW_STEP_NOT_FOUND"  # 工作流步骤不存在
    WORKFLOW_INVALID_STATE = "WORKFLOW_INVALID_STATE"  # 工作流状态不合法

    # ========== Verification 错误（7xxx）==========
    VERIFICATION_FAILED = "VERIFICATION_FAILED"       # 验证失败
    VERIFICATION_TIMEOUT = "VERIFICATION_TIMEOUT"    # 验证超时
    VERIFICATION_CYCLE_EXCEEDED = "VERIFICATION_CYCLE_EXCEEDED"  # 验证循环超限

    # ========== 调度错误（8xxx）==========
    NO_AVAILABLE_AGENT = "NO_AVAILABLE_AGENT"       # 没有可用 Agent
    SCHEDULER_ERROR = "SCHEDULER_ERROR"           # 调度器错误

    # ========== 数据库错误（9xxx）==========
    DB_CONNECTION_ERROR = "DB_CONNECTION_ERROR"     # 数据库连接错误
    DB_WRITE_ERROR = "DB_WRITE_ERROR"             # 数据库写入错误
    DB_CONSTRAINT_VIOLATION = "DB_CONSTRAINT_VIOLATION"  # 约束违反

# 错误码 → HTTP 状态码映射
ERROR_CODE_TO_STATUS = {
    GreverErrorCode.INTERNAL_ERROR: 500,
    GreverErrorCode.VALIDATION_ERROR: 400,
    GreverErrorCode.NOT_FOUND: 404,
    GreverErrorCode.DUPLICATE_ENTRY: 409,
    GreverErrorCode.INVALID_STATE: 400,

    GreverErrorCode.TASK_NOT_FOUND: 404,
    GreverErrorCode.TASK_IN_INVALID_STATE: 400,
    GreverErrorCode.ACCEPTANCE_CRITERIA_REQUIRED: 400,
    GreverErrorCode.TASK_NOT_ASSIGNABLE: 400,
    GreverErrorCode.TASK_BLOCKED_BY_DEPENDENCIES: 400,
    GreverErrorCode.TASK_RETRY_EXHAUSTED: 400,
    GreverErrorCode.TASK_TIMEOUT: 400,

    GreverErrorCode.GOAL_NOT_FOUND: 404,
    GreverErrorCode.GOAL_IN_INVALID_STATE: 400,

    GreverErrorCode.PROJECT_NOT_FOUND: 404,
    GreverErrorCode.PROJECT_IN_INVALID_STATE: 400,

    GreverErrorCode.AGENT_NOT_FOUND: 404,
    GreverErrorCode.AGENT_OFFLINE: 400,
    GreverErrorCode.AGENT_CAPACITY_FULL: 400,

    GreverErrorCode.WORKFLOW_NOT_FOUND: 404,
    GreverErrorCode.WORKFLOW_STEP_NOT_FOUND: 404,
    GreverErrorCode.WORKFLOW_INVALID_STATE: 400,

    GreverErrorCode.VERIFICATION_FAILED: 400,
    GreverErrorCode.VERIFICATION_TIMEOUT: 400,
    GreverErrorCode.VERIFICATION_CYCLE_EXCEEDED: 400,

    GreverErrorCode.NO_AVAILABLE_AGENT: 503,
    GreverErrorCode.SCHEDULER_ERROR: 500,

    GreverErrorCode.DB_CONNECTION_ERROR: 503,
    GreverErrorCode.DB_WRITE_ERROR: 500,
    GreverErrorCode.DB_CONSTRAINT_VIOLATION: 409,
}

# 错误码 → 中文消息映射
ERROR_CODE_TO_MESSAGE = {
    GreverErrorCode.INTERNAL_ERROR: "内部错误",
    GreverErrorCode.VALIDATION_ERROR: "参数校验失败",
    GreverErrorCode.NOT_FOUND: "资源不存在",
    GreverErrorCode.DUPLICATE_ENTRY: "重复条目",
    GreverErrorCode.INVALID_STATE: "状态不合法",

    GreverErrorCode.TASK_NOT_FOUND: "任务不存在",
    GreverErrorCode.TASK_IN_INVALID_STATE: "任务状态不合法，无法执行此操作",
    GreverErrorCode.ACCEPTANCE_CRITERIA_REQUIRED: "必须设置 acceptance_criteria",
    GreverErrorCode.TASK_NOT_ASSIGNABLE: "任务不可分配",
    GreverErrorCode.TASK_BLOCKED_BY_DEPENDENCIES: "任务被依赖阻塞",
    GreverErrorCode.TASK_RETRY_EXHAUSTED: "任务重试次数已耗尽",
    GreverErrorCode.TASK_TIMEOUT: "任务执行超时",

    GreverErrorCode.GOAL_NOT_FOUND: "目标不存在",
    GreverErrorCode.GOAL_IN_INVALID_STATE: "目标状态不合法",

    GreverErrorCode.PROJECT_NOT_FOUND: "项目不存在",
    GreverErrorCode.PROJECT_IN_INVALID_STATE: "项目状态不合法",

    GreverErrorCode.AGENT_NOT_FOUND: "Agent 不存在",
    GreverErrorCode.AGENT_OFFLINE: "Agent 已离线",
    GreverErrorCode.AGENT_CAPACITY_FULL: "Agent 容量已满",

    GreverErrorCode.WORKFLOW_NOT_FOUND: "工作流不存在",
    GreverErrorCode.WORKFLOW_STEP_NOT_FOUND: "工作流步骤不存在",
    GreverErrorCode.WORKFLOW_INVALID_STATE: "工作流状态不合法",

    GreverErrorCode.VERIFICATION_FAILED: "验证失败",
    GreverErrorCode.VERIFICATION_TIMEOUT: "验证超时",
    GreverErrorCode.VERIFICATION_CYCLE_EXCEEDED: "验证循环次数超限",

    GreverErrorCode.NO_AVAILABLE_AGENT: "没有可用 Agent",
    GreverErrorCode.SCHEDULER_ERROR: "调度器错误",

    GreverErrorCode.DB_CONNECTION_ERROR: "数据库连接错误",
    GreverErrorCode.DB_WRITE_ERROR: "数据库写入错误",
    GreverErrorCode.DB_CONSTRAINT_VIOLATION: "数据约束违反",
}
