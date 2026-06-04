"""
EventBus 抽象层 - 统一事件总线，支持 SSE/Poll 两种 Adapter

扩展自 reins/event_bus.py，增加：
- Agent 级别事件类型（task_assigned, task_completed, dispute_raised, etc.）
- Event 持久化到 SQLite 数据库
- trigger_mode 驱动的 Adapter 切换
"""

from .types import (
    EventType,
    AgentEventType,
    Event,
    EventPayload,
    TriggerMode,
)
from .interfaces import IEventBus, IEventAdapter
from .store import EventStore
from .sse_adapter import SseEventAdapter
from .polling_adapter import PollingEventAdapter
from .manager import EventBusManager, get_event_bus_manager

__all__ = [
    "EventType",
    "AgentEventType",
    "Event",
    "EventPayload",
    "TriggerMode",
    "IEventBus",
    "IEventAdapter",
    "EventStore",
    "SseEventAdapter",
    "PollingEventAdapter",
    "EventBusManager",
    "get_event_bus_manager",
]
