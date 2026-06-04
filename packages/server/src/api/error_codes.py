"""
Nexus 错误码定义

所有 API 错误必须使用这里定义的错误码，
禁止在代码中直接返回字符串错误信息。
"""

from enum import Enum

class NexusErrorCode(str, Enum):
    """Nexus 系统错误码"""

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
    NexusErrorCode.INTERNAL_ERROR: 500,
    NexusErrorCode.VALIDATION_ERROR: 400,
    NexusErrorCode.NOT_FOUND: 404,
    NexusErrorCode.DUPLICATE_ENTRY: 409,
    NexusErrorCode.INVALID_STATE: 400,

    NexusErrorCode.TASK_NOT_FOUND: 404,
    NexusErrorCode.TASK_IN_INVALID_STATE: 400,
    NexusErrorCode.ACCEPTANCE_CRITERIA_REQUIRED: 400,
    NexusErrorCode.TASK_NOT_ASSIGNABLE: 400,
    NexusErrorCode.TASK_BLOCKED_BY_DEPENDENCIES: 400,
    NexusErrorCode.TASK_RETRY_EXHAUSTED: 400,
    NexusErrorCode.TASK_TIMEOUT: 400,

    NexusErrorCode.GOAL_NOT_FOUND: 404,
    NexusErrorCode.GOAL_IN_INVALID_STATE: 400,

    NexusErrorCode.PROJECT_NOT_FOUND: 404,
    NexusErrorCode.PROJECT_IN_INVALID_STATE: 400,

    NexusErrorCode.AGENT_NOT_FOUND: 404,
    NexusErrorCode.AGENT_OFFLINE: 400,
    NexusErrorCode.AGENT_CAPACITY_FULL: 400,

    NexusErrorCode.WORKFLOW_NOT_FOUND: 404,
    NexusErrorCode.WORKFLOW_STEP_NOT_FOUND: 404,
    NexusErrorCode.WORKFLOW_INVALID_STATE: 400,

    NexusErrorCode.VERIFICATION_FAILED: 400,
    NexusErrorCode.VERIFICATION_TIMEOUT: 400,
    NexusErrorCode.VERIFICATION_CYCLE_EXCEEDED: 400,

    NexusErrorCode.NO_AVAILABLE_AGENT: 503,
    NexusErrorCode.SCHEDULER_ERROR: 500,

    NexusErrorCode.DB_CONNECTION_ERROR: 503,
    NexusErrorCode.DB_WRITE_ERROR: 500,
    NexusErrorCode.DB_CONSTRAINT_VIOLATION: 409,
}

# 错误码 → 中文消息映射
ERROR_CODE_TO_MESSAGE = {
    NexusErrorCode.INTERNAL_ERROR: "内部错误",
    NexusErrorCode.VALIDATION_ERROR: "参数校验失败",
    NexusErrorCode.NOT_FOUND: "资源不存在",
    NexusErrorCode.DUPLICATE_ENTRY: "重复条目",
    NexusErrorCode.INVALID_STATE: "状态不合法",

    NexusErrorCode.TASK_NOT_FOUND: "任务不存在",
    NexusErrorCode.TASK_IN_INVALID_STATE: "任务状态不合法，无法执行此操作",
    NexusErrorCode.ACCEPTANCE_CRITERIA_REQUIRED: "必须设置 acceptance_criteria",
    NexusErrorCode.TASK_NOT_ASSIGNABLE: "任务不可分配",
    NexusErrorCode.TASK_BLOCKED_BY_DEPENDENCIES: "任务被依赖阻塞",
    NexusErrorCode.TASK_RETRY_EXHAUSTED: "任务重试次数已耗尽",
    NexusErrorCode.TASK_TIMEOUT: "任务执行超时",

    NexusErrorCode.GOAL_NOT_FOUND: "目标不存在",
    NexusErrorCode.GOAL_IN_INVALID_STATE: "目标状态不合法",

    NexusErrorCode.PROJECT_NOT_FOUND: "项目不存在",
    NexusErrorCode.PROJECT_IN_INVALID_STATE: "项目状态不合法",

    NexusErrorCode.AGENT_NOT_FOUND: "Agent 不存在",
    NexusErrorCode.AGENT_OFFLINE: "Agent 已离线",
    NexusErrorCode.AGENT_CAPACITY_FULL: "Agent 容量已满",

    NexusErrorCode.WORKFLOW_NOT_FOUND: "工作流不存在",
    NexusErrorCode.WORKFLOW_STEP_NOT_FOUND: "工作流步骤不存在",
    NexusErrorCode.WORKFLOW_INVALID_STATE: "工作流状态不合法",

    NexusErrorCode.VERIFICATION_FAILED: "验证失败",
    NexusErrorCode.VERIFICATION_TIMEOUT: "验证超时",
    NexusErrorCode.VERIFICATION_CYCLE_EXCEEDED: "验证循环次数超限",

    NexusErrorCode.NO_AVAILABLE_AGENT: "没有可用 Agent",
    NexusErrorCode.SCHEDULER_ERROR: "调度器错误",

    NexusErrorCode.DB_CONNECTION_ERROR: "数据库连接错误",
    NexusErrorCode.DB_WRITE_ERROR: "数据库写入错误",
    NexusErrorCode.DB_CONSTRAINT_VIOLATION: "数据约束违反",
}
