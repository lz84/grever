"""
Task 状态机（P5-03）— 基于 transitions 库

定义 Task 的完整状态转换规则：
- backlog / todo / in_progress / in_review / blocked / done / cancelled / timeout

使用 transitions 库实现状态机，替代手动的 VALID_TRANSITIONS 字典。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from loguru import logger
from transitions import Machine

# 从 centralized enums 导入
from models.enums import TaskState


# =============================================================================
# 状态副作用
# =============================================================================

class TaskStateSideEffects:
    """
    Task 状态副作用（P5-03-03）

    状态变更时自动设置：
    - in_progress: started_at
    - done: completed_at
    - cancelled: cancelled_at
    - blocked: blocked_reason
    """

    @staticmethod
    def apply_side_effects(
        task_dict: Dict[str, Any],
        from_state: TaskState,
        to_state: TaskState,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now()

        if to_state == TaskState.IN_PROGRESS and from_state != TaskState.IN_PROGRESS:
            if not task_dict.get("started_at"):
                task_dict["started_at"] = now

        if to_state == TaskState.DONE:
            task_dict["completed_at"] = now
            task_dict["result"] = task_dict.get("result", "")

        if to_state == TaskState.CANCELLED:
            task_dict["cancelled_at"] = now

        if to_state == TaskState.BLOCKED:
            task_dict["blocked_reason"] = reason or "Unknown reason"
        elif from_state == TaskState.BLOCKED and to_state != TaskState.BLOCKED:
            task_dict["blocked_reason"] = None

        if to_state == TaskState.TIMEOUT:
            task_dict["timeout_reason"] = reason or "任务超时未完成"

        task_dict["updated_at"] = now
        return task_dict


# =============================================================================
# Activity Log
# =============================================================================

@dataclass
class TaskActivityLog:
    """Task 活动日志（P5-03-07）"""
    id: str = ""
    task_id: str = ""
    old_status: str = ""
    new_status: str = ""
    reason: Optional[str] = None
    actor: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "reason": self.reason,
            "actor": self.actor,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "extra": self.extra,
        }


# =============================================================================
# 基于 transitions 的状态机
# =============================================================================

class TaskStateMachine:
    """
    Task 状态机（P5-03-02, P5-03-03, P5-03-07）

    使用 transitions 库管理状态转换。
    """

    # transitions 库定义的状态列表
    STATES = [s.value for s in TaskState]

    # 转换定义：(name, source, dest)
    TRANSITIONS = [
        # backlog → todo / cancelled
        {"trigger": "start", "source": "backlog", "dest": "todo"},
        {"trigger": "cancel", "source": "backlog", "dest": "cancelled"},
        # todo → in_progress / blocked / cancelled
        {"trigger": "progress", "source": "todo", "dest": "in_progress"},
        {"trigger": "block", "source": "todo", "dest": "blocked"},
        {"trigger": "cancel", "source": "todo", "dest": "cancelled"},
        # in_progress → in_review / blocked / cancelled / timeout
        {"trigger": "review", "source": "in_progress", "dest": "in_review"},
        {"trigger": "block", "source": "in_progress", "dest": "blocked"},
        {"trigger": "cancel", "source": "in_progress", "dest": "cancelled"},
        {"trigger": "timeout", "source": "in_progress", "dest": "timeout"},
        # in_review → done / in_progress / blocked / cancelled
        {"trigger": "approve", "source": "in_review", "dest": "done"},
        {"trigger": "rework", "source": "in_review", "dest": "in_progress"},
        {"trigger": "block", "source": "in_review", "dest": "blocked"},
        {"trigger": "cancel", "source": "in_review", "dest": "cancelled"},
        # blocked → todo / cancelled
        {"trigger": "unblock", "source": "blocked", "dest": "todo"},
        {"trigger": "cancel", "source": "blocked", "dest": "cancelled"},
        # done → cancelled (可取消已完成任务)
        {"trigger": "cancel", "source": "done", "dest": "cancelled"},
    ]

    def __init__(self):
        self._activity_logs: List[TaskActivityLog] = []
        self._log_listeners: List[Callable[[TaskActivityLog], None]] = []
        # 创建 transitions 状态机模型
        self._machine = Machine(
            model=self,
            states=self.STATES,
            initial="backlog",
            transitions=self.TRANSITIONS,
            auto_transitions=False,  # 禁用自动转换，只用显式定义的
        )

    def add_log_listener(self, listener: Callable[[TaskActivityLog], None]) -> None:
        """添加 activity_log 监听器"""
        self._log_listeners.append(listener)

    def transition(
        self,
        task_dict: Dict[str, Any],
        to_state: TaskState,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行状态转换

        Args:
            task_dict: 任务属性字典
            to_state: 目标状态
            reason: 变更原因
            actor: 触发者

        Returns:
            更新后的 task_dict

        Raises:
            InvalidStateTransitionError: 非法状态转换
        """
        from_state_str = task_dict.get("status", "backlog")
        from_state = TaskState.from_string(from_state_str)
        to_state_str = to_state.value

        # 相同状态视为幂等
        if from_state_str == to_state_str:
            return task_dict

        # 找到匹配的转换并执行
        if not self._can_transition(from_state_str, to_state_str):
            allowed = self._get_allowed_transitions(from_state_str)
            allowed_str = ", ".join(allowed) if allowed else "none"
            raise InvalidStateTransitionError(
                from_state=from_state.value,
                to_state=to_state.value,
                allowed=allowed_str,
            )

        # 记录 activity log
        log = TaskActivityLog(
            task_id=task_dict.get("id", ""),
            old_status=from_state.value,
            new_status=to_state.value,
            reason=reason,
            actor=actor,
            timestamp=datetime.now(),
        )
        self._activity_logs.append(log)

        # 通知监听器
        for listener in self._log_listeners:
            try:
                listener(log)
            except Exception as e:
                logger.error(f"[TaskStateMachine] Log listener error: {e}")

        # 设置状态机当前状态
        self.state = from_state_str

        # 执行转换
        trigger_name = self._find_trigger(from_state_str, to_state_str)
        if trigger_name:
            getattr(self, trigger_name)()

        # 应用副作用
        task_dict = TaskStateSideEffects.apply_side_effects(
            task_dict, from_state, to_state, reason,
        )

        # 更新状态字段
        task_dict["status"] = to_state.to_legacy()

        return task_dict

    def _can_transition(self, from_state: str, to_state: str) -> bool:
        """检查状态转换是否合法"""
        for t in self.TRANSITIONS:
            src = t["source"]
            if src == "*":
                return True
            if isinstance(src, list):
                if from_state in src and t["dest"] == to_state:
                    return True
            elif src == from_state and t["dest"] == to_state:
                return True
        return False

    def _get_allowed_transitions(self, from_state: str) -> List[str]:
        """获取允许的目标状态"""
        targets = set()
        for t in self.TRANSITIONS:
            src = t["source"]
            if src == "*" or src == from_state or (isinstance(src, list) and from_state in src):
                targets.add(t["dest"])
        return sorted(targets)

    def _find_trigger(self, from_state: str, to_state: str) -> Optional[str]:
        """找到匹配的 trigger 名称"""
        for t in self.TRANSITIONS:
            src = t["source"]
            if src == from_state and t["dest"] == to_state:
                return t["trigger"]
            if src == "*" and t["dest"] == to_state:
                return t["trigger"]
            if isinstance(src, list) and from_state in src and t["dest"] == to_state:
                return t["trigger"]
        return None

    def get_activity_logs(self, task_id: Optional[str] = None) -> List[TaskActivityLog]:
        """获取 activity logs"""
        if task_id:
            return [log for log in self._activity_logs if log.task_id == task_id]
        return list(self._activity_logs)


# =============================================================================
# 异常定义
# =============================================================================

class InvalidStateTransitionError(Exception):
    """非法状态转换异常（P5-03-02）"""

    def __init__(
        self,
        from_state: str,
        to_state: str,
        allowed: str = "",
        task_id: str = "",
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.allowed = allowed
        self.task_id = task_id

        msg = f"Invalid state transition: {from_state} → {to_state}"
        if allowed:
            msg += f" (allowed: {allowed})"
        if task_id:
            msg = f"Task {task_id}: {msg}"

        super().__init__(msg)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": "invalid_state_transition",
            "from_state": self.from_state,
            "to_state": self.to_state,
            "allowed_transitions": self.allowed.split(", ") if self.allowed else [],
            "task_id": self.task_id,
        }


# =============================================================================
# 向后兼容：TaskStateTransition 类
# =============================================================================

class TaskStateTransition:
    """
    Task 状态转换规则（向后兼容层）

    使用 transitions 状态机验证转换。
    """

    _sm = None

    @classmethod
    def _get_machine(cls) -> TaskStateMachine:
        if cls._sm is None:
            cls._sm = TaskStateMachine()
        return cls._sm

    @classmethod
    def can_transition(cls, from_state: TaskState, to_state: TaskState) -> bool:
        """检查状态转换是否合法"""
        if from_state == to_state:
            return True
        sm = cls._get_machine()
        return sm._can_transition(from_state.value, to_state.value)

    @classmethod
    def get_allowed_transitions(cls, from_state: TaskState) -> set:
        """获取允许的目标状态"""
        sm = cls._get_machine()
        targets = sm._get_allowed_transitions(from_state.value)
        return {TaskState(t) for t in targets}
