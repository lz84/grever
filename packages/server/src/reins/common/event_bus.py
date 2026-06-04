"""
EventBus 抽象层 - 统一事件总线，支持 SSE/Poll 两种 Adapter

设计：
- EventBus: 抽象基类（ABC），定义统一接口
- SSEEventBus: SSE 适配器，维护客户端连接池
- PollEventBus: 轮询适配器，基于内存 buffer + 增量拉取
- UnifiedEventBus: 路由器，统一管理多个 adapter

使用：
    from reins.common.event_bus import get_event_bus, make_tracker_callback
    event_bus = get_event_bus()  # 返回 UnifiedEventBus（默认包含 SSE + Poll）
"""

import asyncio
import json
from loguru import logger
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set

# ============================================================================
# 事件类型枚举
# ============================================================================

class EventType(str, Enum):
    """工作流事件类型"""
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

# ============================================================================
# 事件数据模型
# ============================================================================

@dataclass
class WorkflowEvent:
    """工作流事件"""
    event_type: str
    workflow_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    step_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_sse_data(self) -> dict:
        """转换为 SSE 推送格式"""
        return asdict(self)

    def to_sse_message(self) -> str:
        """格式化为 SSE 消息字符串"""
        data = json.dumps(self.to_sse_data(), ensure_ascii=False)
        return f"id: {self.event_id}\nevent: {self.event_type}\ndata: {data}\n\n"

    def to_dict(self) -> dict:
        """转换为普通字典（用于 Poll 返回）"""
        return asdict(self)

# ============================================================================
# EventBus 抽象基类
# ============================================================================

class EventBus(ABC):
    """
    事件总线抽象接口

    所有 adapter 必须实现以下方法：
    - subscribe: 订阅特定事件类型
    - subscribe_global: 订阅所有事件
    - publish: 发布事件
    - emit: 便捷发布
    - get_stats: 获取统计信息
    """

    @abstractmethod
    def subscribe(
        self,
        event_type: str,
        callback: Callable[[WorkflowEvent], None],
    ) -> Callable[[], None]:
        """
        订阅特定事件类型
        返回取消订阅函数
        """

    @abstractmethod
    def subscribe_global(
        self,
        callback: Callable[[WorkflowEvent], None],
    ) -> Callable[[], None]:
        """
        订阅所有事件
        返回取消订阅函数
        """

    @abstractmethod
    def publish(self, event: WorkflowEvent) -> None:
        """发布事件到所有订阅者"""

    @abstractmethod
    def emit(
        self,
        event_type: str,
        workflow_id: str,
        step_id: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """便捷发布方法"""

    @abstractmethod
    def get_stats(self) -> dict:
        """获取总线统计信息"""

# ============================================================================
# SSE Event Bus Adapter
# ============================================================================

class SSEEventBus(EventBus):
    """
    SSE 事件总线适配器

    维护 SSE 客户端连接池，通过 queue 异步推送事件。
    适用于实时性要求高的场景。
    """

    def __init__(self, max_queue_size: int = 100):
        # 订阅者
        self._subscribers: Dict[str, List[Callable[[WorkflowEvent], None]]] = defaultdict(list)
        self._global_subscribers: List[Callable[[WorkflowEvent], None]] = []

        # SSE 客户端
        self._sse_clients: Dict[str, dict] = {}
        self._client_lock = asyncio.Lock()
        self._max_queue_size = max_queue_size

        logger.info("[SSEEventBus] Initialized")

    # ---- 订阅 API ----

    def subscribe(
        self,
        event_type: str,
        callback: Callable[[WorkflowEvent], None],
    ) -> Callable[[], None]:
        """订阅特定事件类型"""
        self._subscribers[event_type].append(callback)
        logger.debug(f"[SSEEventBus] Subscribed to {event_type}, total: {len(self._subscribers[event_type])}")

        def unsubscribe():
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

        return unsubscribe

    def subscribe_global(
        self,
        callback: Callable[[WorkflowEvent], None],
    ) -> Callable[[], None]:
        """订阅所有事件"""
        self._global_subscribers.append(callback)

        def unsubscribe():
            if callback in self._global_subscribers:
                self._global_subscribers.remove(callback)

        return unsubscribe

    async def subscribe_sse(
        self,
        workflow_ids: Optional[List[str]] = None,
    ) -> tuple[str, asyncio.Queue]:
        """
        注册 SSE 客户端
        返回 (client_id, event_queue)
        """
        client_id = str(uuid.uuid4())
        queue: asyncio.Queue[Optional[WorkflowEvent]] = asyncio.Queue(maxsize=self._max_queue_size)

        async with self._client_lock:
            self._sse_clients[client_id] = {
                "queue": queue,
                "workflow_ids": set(workflow_ids) if workflow_ids else None,
                "connected_at": datetime.now(),
                "event_count": 0,
            }

        logger.info(f"[SSEEventBus] SSE client registered: {client_id}")
        return client_id, queue

    async def unsubscribe_sse(self, client_id: str) -> None:
        """注销 SSE 客户端"""
        async with self._client_lock:
            if client_id in self._sse_clients:
                del self._sse_clients[client_id]
                logger.info(f"[SSEEventBus] SSE client unregistered: {client_id}")

    # ---- 发布 API ----

    def publish(self, event: WorkflowEvent) -> None:
        """发布事件"""
        # 通知特定类型订阅者
        for cb in list(self._subscribers.get(event.event_type, [])):
            try:
                cb(event)
            except Exception as e:
                logger.error(f"[SSEEventBus] Callback error for {event.event_type}: {e}")

        # 通知全局订阅者
        for cb in list(self._global_subscribers):
            try:
                cb(event)
            except Exception as e:
                logger.error(f"[SSEEventBus] Global callback error: {e}")

        # 推送给 SSE 客户端
        try:
            asyncio.create_task(self._push_to_sse_clients(event))
        except RuntimeError:
            # 没有运行中的 event loop（如测试环境），跳过异步推送
            pass

    def emit(
        self,
        event_type: str,
        workflow_id: str,
        step_id: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """便捷发布"""
        event = WorkflowEvent(
            event_type=event_type,
            workflow_id=workflow_id,
            step_id=step_id,
            data=data or {},
        )
        self.publish(event)

    # ---- SSE 推送 ----

    async def _push_to_sse_clients(self, event: WorkflowEvent) -> None:
        """推送事件给所有匹配的 SSE 客户端"""
        async with self._client_lock:
            clients = list(self._sse_clients.items())

        for client_id, client_info in clients:
            try:
                filter_workflows = client_info.get("workflow_ids")
                if filter_workflows is not None and event.workflow_id not in filter_workflows:
                    continue

                try:
                    client_info["queue"].put_nowait(event)
                    client_info["event_count"] += 1
                except asyncio.QueueFull:
                    logger.warning(f"[SSEEventBus] SSE client {client_id} queue full, dropping event")
            except Exception as e:
                logger.error(f"[SSEEventBus] Error pushing to SSE client {client_id}: {e}")

    # ---- 状态 ----

    def get_client_count(self) -> int:
        return len(self._sse_clients)

    def get_stats(self) -> dict:
        return {
            "type": "sse",
            "active_clients": len(self._sse_clients),
            "subscribers": {k: len(v) for k, v in self._subscribers.items()},
            "global_subscribers": len(self._global_subscribers),
        }

# ============================================================================
# Poll Event Bus Adapter
# ============================================================================

class PollEventBus(EventBus):
    """
    轮询事件总线适配器

    基于内存 buffer 存储最近事件，支持 last_event_id 增量拉取。
    适用于不允许 WebSocket/SSE 或需要按需拉取的场景。

    特性：
    - deque(maxlen=N) 自动淘汰旧事件
    - last_event_id 增量拉取（只返回之后的事件）
    - TTL 过期自动清理
    - workflow_id 过滤
    """

    def __init__(self, max_events: int = 100, ttl_seconds: float = 300.0):
        # 订阅者（保留接口一致性）
        self._subscribers: Dict[str, List[Callable[[WorkflowEvent], None]]] = defaultdict(list)
        self._global_subscribers: List[Callable[[WorkflowEvent], None]] = []

        # 事件 buffer
        self._events: Deque[WorkflowEvent] = deque(maxlen=max_events)
        self._event_index: Dict[str, int] = {}  # event_id -> 在 deque 中的逻辑索引
        self._index_counter = 0

        # 配置
        self._max_events = max_events
        self._ttl_seconds = ttl_seconds

        logger.info(f"[PollEventBus] Initialized (max_events={max_events}, ttl={ttl_seconds}s)")

    # ---- 订阅 API ----

    def subscribe(
        self,
        event_type: str,
        callback: Callable[[WorkflowEvent], None],
    ) -> Callable[[], None]:
        """订阅特定事件类型"""
        self._subscribers[event_type].append(callback)

        def unsubscribe():
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

        return unsubscribe

    def subscribe_global(
        self,
        callback: Callable[[WorkflowEvent], None],
    ) -> Callable[[], None]:
        """订阅所有事件"""
        self._global_subscribers.append(callback)

        def unsubscribe():
            if callback in self._global_subscribers:
                self._global_subscribers.remove(callback)

        return unsubscribe

    # ---- 发布 API ----

    def publish(self, event: WorkflowEvent) -> None:
        """发布事件到 buffer 和订阅者"""
        # 通知订阅者
        for cb in list(self._subscribers.get(event.event_type, [])):
            try:
                cb(event)
            except Exception as e:
                logger.error(f"[PollEventBus] Callback error: {e}")

        for cb in list(self._global_subscribers):
            try:
                cb(event)
            except Exception as e:
                logger.error(f"[PollEventBus] Global callback error: {e}")

        # 存入 buffer
        self._index_counter += 1
        self._events.append(event)
        self._event_index[event.event_id] = self._index_counter

        # 清理过期索引
        self._cleanup_expired_index()

    def emit(
        self,
        event_type: str,
        workflow_id: str,
        step_id: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """便捷发布"""
        event = WorkflowEvent(
            event_type=event_type,
            workflow_id=workflow_id,
            step_id=step_id,
            data=data or {},
        )
        self.publish(event)

    # ---- 轮询 API ----

    def get_events_after(
        self,
        last_event_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        """
        获取 last_event_id 之后的事件（增量拉取）

        Args:
            last_event_id: 上次收到的最后一个事件 ID，None 表示从头获取
            workflow_id: 过滤特定工作流，None 表示不过滤
            limit: 最大返回数量

        Returns:
            事件列表（字典格式）
        """
        # 清理过期事件
        self._cleanup_expired_events()

        # 找到起始位置
        start_index = 0
        if last_event_id and last_event_id in self._event_index:
            last_idx = self._event_index[last_event_id]
            # 找到 deque 中第一个索引 > last_idx 的位置
            for i, event in enumerate(self._events):
                event_idx = self._event_index.get(event.event_id, 0)
                if event_idx > last_idx:
                    start_index = i
                    break
            else:
                # 没有找到更新的 event，返回空
                return []

        # 收集事件
        results = []
        for event in list(self._events)[start_index:]:
            if workflow_id and event.workflow_id != workflow_id:
                continue
            results.append(event.to_dict())
            if len(results) >= limit:
                break

        return results

    # ---- 清理 ----

    def _cleanup_expired_events(self) -> None:
        """清理过期事件"""
        cutoff = time.time() - self._ttl_seconds
        removed = 0
        while self._events:
            event = self._events[0]
            try:
                ts = datetime.fromisoformat(event.timestamp).timestamp()
            except (ValueError, TypeError):
                ts = 0
            if ts < cutoff:
                self._events.popleft()
                self._event_index.pop(event.event_id, None)
                removed += 1
            else:
                break

        if removed:
            logger.debug(f"[PollEventBus] Cleaned up {removed} expired events")

    def _cleanup_expired_index(self) -> None:
        """清理 deque 中已淘汰事件的索引"""
        event_ids_in_deque = {e.event_id for e in self._events}
        stale_keys = [k for k in self._event_index if k not in event_ids_in_deque]
        for k in stale_keys:
            del self._event_index[k]

    # ---- 状态 ----

    def get_stats(self) -> dict:
        return {
            "type": "poll",
            "buffer_size": len(self._events),
            "max_events": self._max_events,
            "ttl_seconds": self._ttl_seconds,
            "index_size": len(self._event_index),
            "subscribers": {k: len(v) for k, v in self._subscribers.items()},
        }

# ============================================================================
# Unified Event Bus Router
# ============================================================================

class UnifiedEventBus(EventBus):
    """
    统一事件总线路由器

    管理多个 EventBus adapter，发布事件时同时通知所有 adapter。
    提供统一的 subscribe/publish 接口，内部路由到各个 adapter。
    """

    def __init__(self):
        self._adapters: List[EventBus] = []
        # Unified 自身的订阅者（独立于 adapter）
        self._subscribers: Dict[str, List[Callable[[WorkflowEvent], None]]] = defaultdict(list)
        self._global_subscribers: List[Callable[[WorkflowEvent], None]] = []

        logger.info("[UnifiedEventBus] Initialized")

    def register(self, adapter: EventBus) -> None:
        """注册一个 adapter"""
        self._adapters.append(adapter)
        logger.info(f"[UnifiedEventBus] Registered adapter: {adapter.__class__.__name__}")

    def unregister(self, adapter: EventBus) -> None:
        """注销一个 adapter"""
        if adapter in self._adapters:
            self._adapters.remove(adapter)
            logger.info(f"[UnifiedEventBus] Unregistered adapter: {adapter.__class__.__name__}")

    def get_adapter(self, adapter_type: type) -> Optional[EventBus]:
        """按类型获取 adapter"""
        for adapter in self._adapters:
            if isinstance(adapter, adapter_type):
                return adapter
        return None

    # ---- 订阅 API ----

    def subscribe(
        self,
        event_type: str,
        callback: Callable[[WorkflowEvent], None],
    ) -> Callable[[], None]:
        """订阅事件（同时在所有 adapter 上订阅）"""
        unsubscribes = []
        for adapter in self._adapters:
            unsubscribes.append(adapter.subscribe(event_type, callback))
        self._subscribers[event_type].append(callback)

        def unsubscribe():
            for unsub in unsubscribes:
                unsub()
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

        return unsubscribe

    def subscribe_global(
        self,
        callback: Callable[[WorkflowEvent], None],
    ) -> Callable[[], None]:
        """订阅所有事件"""
        unsubscribes = []
        for adapter in self._adapters:
            unsubscribes.append(adapter.subscribe_global(callback))
        self._global_subscribers.append(callback)

        def unsubscribe():
            for unsub in unsubscribes:
                unsub()
            if callback in self._global_subscribers:
                self._global_subscribers.remove(callback)

        return unsubscribe

    # ---- 发布 API ----

    def publish(self, event: WorkflowEvent) -> None:
        """发布事件到所有 adapter"""
        # 通知自身订阅者
        for cb in list(self._subscribers.get(event.event_type, [])):
            try:
                cb(event)
            except Exception as e:
                logger.error(f"[UnifiedEventBus] Callback error: {e}")
        for cb in list(self._global_subscribers):
            try:
                cb(event)
            except Exception as e:
                logger.error(f"[UnifiedEventBus] Global callback error: {e}")

        # 通知所有 adapter
        for adapter in self._adapters:
            try:
                adapter.publish(event)
            except Exception as e:
                logger.error(f"[UnifiedEventBus] Adapter {adapter.__class__.__name__} publish error: {e}")

    def emit(
        self,
        event_type: str,
        workflow_id: str,
        step_id: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """便捷发布"""
        event = WorkflowEvent(
            event_type=event_type,
            workflow_id=workflow_id,
            step_id=step_id,
            data=data or {},
        )
        self.publish(event)

    # ---- 状态 ----

    def get_stats(self) -> dict:
        return {
            "type": "unified",
            "adapter_count": len(self._adapters),
            "adapters": [a.get_stats() for a in self._adapters],
            "global_subscribers": len(self._global_subscribers),
        }

# ============================================================================
# 全局单例与辅助函数
# ============================================================================

_event_bus: Optional[UnifiedEventBus] = None

def get_event_bus() -> UnifiedEventBus:
    """
    获取全局统一事件总线（单例）

    首次调用时自动创建 UnifiedEventBus 并注册 SSE + Poll adapter。
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = UnifiedEventBus()
        _event_bus.register(SSEEventBus())
        _event_bus.register(PollEventBus())
        logger.info("[EventBus] Global unified event bus initialized with SSE + Poll adapters")
    return _event_bus

def reset_event_bus() -> None:
    """重置全局事件总线（主要用于测试）"""
    global _event_bus
    _event_bus = None

def get_sse_adapter() -> Optional[SSEEventBus]:
    """获取 SSE adapter（用于 SSE 端点注册客户端）"""
    bus = get_event_bus()
    adapter = bus.get_adapter(SSEEventBus)
    if isinstance(adapter, SSEEventBus):
        return adapter
    return None

def get_poll_adapter() -> Optional[PollEventBus]:
    """获取 Poll adapter（用于 Poll 端点查询事件）"""
    bus = get_event_bus()
    adapter = bus.get_adapter(PollEventBus)
    if isinstance(adapter, PollEventBus):
        return adapter
    return None

# ============================================================================
# Tracker 回调（向后兼容）
# ============================================================================

def make_tracker_callback(event_bus: Optional[EventBus] = None) -> Callable[[dict], None]:
    """
    创建 tracker 回调函数，将 WorkflowExecutionEngine 的事件转发到 EventBus

    向后兼容：不传 event_bus 时自动使用全局事件总线。
    """
    bus = event_bus or get_event_bus()

    def callback(event_data: dict):
        event_type = event_data.get("event_type", "")
        workflow_id = event_data.get("workflow_id", "")
        step_id = event_data.get("step_id", "")
        data = event_data.get("data", {})

        # 映射 tracker 事件类型到 EventBus 类型
        type_mapping = {
            "step_started": EventType.STEP_STARTED,
            "step_completed": EventType.STEP_COMPLETED,
            "step_failed": EventType.STEP_FAILED,
            "step_cancelled": EventType.STEP_FAILED,
            "workflow_started": EventType.WORKFLOW_STARTED,
            "workflow_completed": EventType.WORKFLOW_COMPLETED,
            "workflow_error": EventType.WORKFLOW_FAILED,
            "workflow_paused": EventType.WORKFLOW_PAUSED,
            "workflow_resumed": EventType.WORKFLOW_RESUMED,
            "workflow_cancelled": EventType.WORKFLOW_CANCELLED,
            "step_added": EventType.STEP_ADDED,
            "steps_blocked": EventType.STEPS_BLOCKED,
        }

        bus_event_type = type_mapping.get(event_type, event_type)
        if isinstance(bus_event_type, EventType):
            bus_event_type = bus_event_type.value

        bus.emit(
            event_type=bus_event_type,
            workflow_id=workflow_id,
            step_id=step_id,
            data=data,
        )

    return callback
