"""
Reins 枚举定义

所有核心枚举类集中在此，便于管理和导入。
从 _legacy_models.py 迁移而来。
"""

from enum import Enum


class GoalStatus(str, Enum):
    """目标状态"""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectStatus(str, Enum):
    """项目状态"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    ON_HOLD = "on_hold"


class TaskStatus(str, Enum):
    """
    任务状态（P5-03-01）

    7个状态：backlog / todo / in_progress / in_review / blocked / done / cancelled
    向后兼容旧状态名：pending→todo, running→in_progress, completed→done
    """
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"

    @classmethod
    def from_string(cls, value: str) -> "TaskStatus":
        """从字符串转换（兼容旧状态名）"""
        mapping = {
            "backlog": cls.BACKLOG,
            "todo": cls.TODO,
            "in_progress": cls.IN_PROGRESS,
            "in_review": cls.IN_REVIEW,
            "blocked": cls.BLOCKED,
            "done": cls.DONE,
            "cancelled": cls.CANCELLED,
            "pending": cls.TODO,
            "running": cls.IN_PROGRESS,
            "completed": cls.DONE,
        }
        return mapping.get(value.lower(), cls.TODO)


class AgentStatus(str, Enum):
    """Agent 状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    IDLE = "idle"


class TriggerMode(str, Enum):
    """Agent 触发模式（P5-05）"""
    SSE = "sse"
    POLLING = "polling"


class DisputeType(str, Enum):
    """争议类型"""
    RESOURCE_CONFLICT = "resource_conflict"
    TASK_CONFLICT = "task_conflict"
    PERMISSION_CONFLICT = "permission_conflict"
    STATE_CONFLICT = "state_conflict"


class DisputeStatus(str, Enum):
    """争议状态"""
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    APPEALED = "appealed"
    CLOSED = "closed"


class Priority(int, Enum):
    """优先级"""
    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3


# ---- state_machine 状态枚举（从 state_machine.py 迁移） ----

class TaskState(str, Enum):
    """
    Task 完整状态枚举（P5-03-01）

    8个状态：
    - backlog: 待办池（初始状态）
    - todo: 已确认待做
    - in_progress: 进行中
    - in_review: 审核中
    - blocked: 阻塞
    - done: 已完成
    - cancelled: 已取消
    - timeout: 超时（自动回收）
    """
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

    @classmethod
    def from_string(cls, value: str) -> "TaskState":
        """从字符串转换（兼容旧状态名）"""
        mapping = {
            "backlog": cls.BACKLOG,
            "todo": cls.TODO,
            "in_progress": cls.IN_PROGRESS,
            "in_review": cls.IN_REVIEW,
            "blocked": cls.BLOCKED,
            "done": cls.DONE,
            "cancelled": cls.CANCELLED,
            "timeout": cls.TIMEOUT,
            "pending": cls.TODO,
            "running": cls.IN_PROGRESS,
            "completed": cls.DONE,
        }
        return mapping.get(value.lower(), cls.TODO)

    def to_legacy(self) -> str:
        """转换为旧状态名（向后兼容）"""
        return self.value
