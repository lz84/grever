"""
Polling Event Adapter（P5-01-04）

实现 IEventAdapter 接口，支持：
- 轮询拉取未读事件
- 分页查询
- last_event_id 增量拉取
- 事件去重（read_at 标记）
"""

import logging
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Callable, Deque, Dict, List, Optional

from shared.eventbus.interfaces import IEventAdapter
from shared.eventbus.types import Event, EventPayload, TriggerMode
from shared.eventbus.store import EventStore

logger = logging.getLogger(__name__)


class PollingEventAdapter(IEventAdapter):
    """
    轮询事件适配器（P5-01-04）

    特性：
    - 轮询拉取未读事件（基于 EventStore DB 查询）
    - 分页查询（limit/offset）
    - last_event_id 增量拉取（支持断点续传）
    - TTL 过期自动清理内存 buffer
    """

    def __init__(
        self,
        event_store: Optional[EventStore] = None,
        max_memory_events: int = 200,
        ttl_seconds: float = 300.0,
    ):
        self._event_store = event_store or EventStore()
        self._memory_buffer: Deque[Event] = deque(maxlen=max_memory_events)
        self._memory_index: Dict[str, int] = {}  # event_id → buffer index
        self._ttl_seconds = ttl_seconds
        self._max_memory_events = max_memory_events

        # 内存订阅（仅用于向后兼容回调，polling 模式主要用 DB）
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = defaultdict(list)
        self._global_subscribers: List[Callable[[Event], None]] = []

        # agent 配置缓存（agent_id → trigger_mode）
        self._agent_configs: Dict[str, Dict[str, Any]] = {}

        logger.info(f"[PollingEventAdapter] Initialized (ttl={ttl_seconds}s, memory_buffer={max_memory_events})")

    @property
    def trigger_mode(self) -> TriggerMode:
        return TriggerMode.POLLING

    def subscribe(self, agent_id: str, event_types: Optional[List[str]] = None) -> str:
        """
        注册轮询订阅（仅记录配置，不建立长连接）
        返回 subscription_id
        """
        subscription_id = str(uuid.uuid4())
        self._agent_configs[agent_id] = {
            "subscription_id": subscription_id,
            "event_types": set(event_types) if event_types else None,
            "registered_at": datetime.now(),
        }
        logger.info(f"[PollingEventAdapter] Subscribed agent={agent_id}, subscription={subscription_id}")
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> None:
        """取消订阅"""
        # 从 agent_configs 中找到并移除
        for agent_id, cfg in list(self._agent_configs.items()):
            if cfg.get("subscription_id") == subscription_id:
                del self._agent_configs[agent_id]
                logger.info(f"[PollingEventAdapter] Unsubscribed subscription={subscription_id}")
                return

    def get_pending(self, agent_id: str, since: Optional[str] = None) -> List[Event]:
        """
        获取待处理事件（轮询适配器核心方法，P5-01-04）

        - agent_id: Agent ID
        - since: 上次获取的时间戳（ISO 格式），None 表示从头

        实现策略：
        1. 先清理过期内存事件
        2. 如果 since 为 None，从 DB 加载并缓存到内存
        3. 返回未读事件（按 created_at 升序）
        """
        # 获取 agent 订阅配置
        config = self._agent_configs.get(agent_id, {})
        event_types_filter = config.get("event_types")

        # 清理过期内存
        self._cleanup_memory()

        # 优先使用 DB 查询（支持分页、增量）
        if self._event_store:
            db_events = self._event_store.get_pending(
                agent_id=agent_id,
                since=since,
                event_types=list(event_types_filter) if event_types_filter else None,
                limit=100,
            )
            # 同时更新内存 buffer
            for event in db_events:
                if event.event_id not in self._memory_index:
                    self._memory_buffer.append(event)
                    self._memory_index[event.event_id] = len(self._memory_buffer) - 1
            return db_events

        # 兜底：纯内存查询
        return self._get_from_memory(agent_id, since, event_types_filter)

    def _get_from_memory(
        self,
        agent_id: str,
        since: Optional[str],
        event_types_filter: Optional[set],
    ) -> List[Event]:
        """从内存 buffer 查询"""
        since_ts = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
                since_ts = since_dt.timestamp()
            except (ValueError, TypeError):
                since_ts = None

        results = []
        for event in self._memory_buffer:
            if event.agent_id and event.agent_id != agent_id:
                continue
            if since_ts:
                event_ts = event.created_at.timestamp() if event.created_at else 0
                if event_ts <= since_ts:
                    continue
            if event_types_filter and event.event_type not in event_types_filter:
                continue
            results.append(event)

        return results

    def publish(self, event: Event) -> None:
        """
        发布事件（轮询适配器）
        注：DB 持久化由 EventBusManager.publish 统一处理，这里不重复保存
        1. 存入内存 buffer
        2. 通知订阅者
        """
        # DB 持久化已由 Manager 处理，不再重复 save

        # 存入内存 buffer
        self._memory_buffer.append(event)
        self._memory_index[event.event_id] = len(self._memory_buffer) - 1

        # 通知订阅者
        for cb in self._subscribers.get(event.event_type, []):
            try:
                cb(event)
            except Exception as e:
                logger.error(f"[PollingEventAdapter] Callback error: {e}")

        for cb in self._global_subscribers:
            try:
                cb(event)
            except Exception as e:
                logger.error(f"[PollingEventAdapter] Global callback error: {e}")

    def mark_read(self, event_ids: List[str]) -> int:
        """标记事件为已读"""
        if self._event_store:
            return self._event_store.mark_read(event_ids)
        return 0

    def _cleanup_memory(self) -> None:
        """清理过期内存事件"""
        cutoff = time.time() - self._ttl_seconds
        removed = 0

        while self._memory_buffer:
            event = self._memory_buffer[0]
            try:
                ts = event.created_at.timestamp() if event.created_at else 0
                if ts < cutoff:
                    self._memory_buffer.popleft()
                    self._memory_index.pop(event.event_id, None)
                    removed += 1
                else:
                    break
            except (ValueError, TypeError):
                self._memory_buffer.popleft()
                removed += 1

        if removed:
            logger.debug(f"[PollingEventAdapter] Cleaned {removed} expired memory events")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "polling",
            "memory_buffer_size": len(self._memory_buffer),
            "memory_index_size": len(self._memory_index),
            "ttl_seconds": self._ttl_seconds,
            "subscribed_agents": len(self._agent_configs),
            "subscribers": {k: len(v) for k, v in self._subscribers.items()},
        }

    def get_page(
        self,
        agent_id: str,
        page: int = 1,
        page_size: int = 20,
        event_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        分页查询事件（用于管理界面）

        Returns:
            {
                "events": [...],
                "page": 1,
                "page_size": 20,
                "total": 100,
                "has_more": true,
            }
        """
        if not self._event_store:
            # 兜底内存
            events = list(self._memory_buffer)
            total = len(events)
            start = (page - 1) * page_size
            page_events = events[start:start + page_size]
        else:
            events = self._event_store.get_pending(
                agent_id=agent_id,
                event_types=event_types,
                limit=10000,
            )
            total = len(events)
            start = (page - 1) * page_size
            page_events = events[start:start + page_size]

        return {
            "events": [e.to_dict() for e in page_events],
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_more": start + page_size < total,
        }
