"""
EventBus 类型定义

包括：
- EventType: 工作流级别事件类型
- AgentEventType: Agent 级别事件类型
- Event: 事件数据模型
- TriggerMode: 触发模式枚举
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import uuid
import json


class EventType(str, Enum):
    """工作流事件类型（Workflow-level events）"""
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_BLOCKED = "step_blocked"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    CONFLICT_DETECTED = "conflict_detected"
    STEP_ADDED = "step_added"
    STEPS_BLOCKED = "steps_blocked"


class AgentEventType(str, Enum):
    """Agent 级别事件类型（P5-01-02）"""
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    DISPUTE_RAISED = "dispute_raised"
    AGENT_STATUS_CHANGED = "agent_status_changed"
    GOAL_UPDATED = "goal_updated"
    MODE_SWITCHED = "mode_switched"
    TASK_BLOCKED = "task_blocked"
    TASK_UNBLOCKED = "task_unblocked"
    WORKFLOW_STEP_BLOCKED = "workflow_step_blocked"
    WORKFLOW_STEP_UNBLOCKED = "workflow_step_unblocked"


class TriggerMode(str, Enum):
    """Agent 触发模式（P5-01-05）"""
    SSE = "sse"           # Server-Sent Events (实时推送)
    POLLING = "polling"   # 客户端轮询
    CALLBACK = "callback"  # 回调模式


@dataclass
class EventPayload:
    """事件负载（P5-01-02）"""
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    goal_id: Optional[str] = None
    agent_id: Optional[str] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    dispute_id: Optional[str] = None
    blocked_reason: Optional[str] = None
    workflow_id: Optional[str] = None
    step_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Event:
    """
    统一事件模型（P5-01-02, P5-01-06）

    字段：
    - event_id: 全局唯一事件 ID
    - agent_id: 关联的 Agent ID（用于路由和过滤）
    - event_type: 事件类型（工作流或 Agent 事件）
    - payload: 事件负载（JSON）
    - created_at: 创建时间
    - read_at: 已读时间（用于轮询去重）
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: Optional[str] = None
    event_type: str = ""
    payload: EventPayload = field(default_factory=EventPayload)
    created_at: datetime = field(default_factory=datetime.now)
    read_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 API 返回和 DB 存储）"""
        return {
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "event_type": self.event_type,
            "payload": self.payload.to_dict(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }

    def to_sse_message(self) -> str:
        """格式化为 SSE 消息字符串"""
        data = json.dumps(self.to_dict(), ensure_ascii=False)
        return f"id: {self.event_id}\nevent: {self.event_type}\ndata: {data}\n\n"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """从字典创建 Event（用于从 DB 加载）"""
        payload_data = data.get("payload", {})
        if isinstance(payload_data, str):
            payload_data = json.loads(payload_data)
        payload = EventPayload(**payload_data)
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        read_at = data.get("read_at")
        if isinstance(read_at, str):
            read_at = datetime.fromisoformat(read_at)
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            agent_id=data.get("agent_id"),
            event_type=data.get("event_type", ""),
            payload=payload,
            created_at=created_at or datetime.now(),
            read_at=read_at,
        )
