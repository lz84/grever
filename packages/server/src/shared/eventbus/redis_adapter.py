"""
Redis Pub/Sub EventBus Adapter (P3-4)

提供 Redis  Pub/Sub 事件发布/订阅支持：
- 发布事件时同时推送到 Redis channel
- 订阅同一个 channel 的多个进程/实例可以收到事件
- 无 Redis 时自动降级为内存（兼容 EventBusManager）

用法：
    from shared.eventbus.redis_adapter import RedisEventAdapter
    adapter = RedisEventAdapter(redis_url="redis://localhost:6379/0")
    manager.register_adapter(adapter)
"""

import json
import logging
import threading
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from shared.eventbus.interfaces import IEventAdapter
from shared.eventbus.types import Event, EventPayload, TriggerMode

logger = logging.getLogger(__name__)

REDIS_CHANNEL_PREFIX = "nexus:events:"
REDIS_EVENT_TYPES = [
    "task_assigned", "task_completed", "task_failed",
    "task_created", "task_updated", "dispute_raised",
    "agent_status_changed", "mode_switched",
    "step_started", "step_completed", "step_failed",
    "workflow_started", "workflow_completed", "workflow_failed",
]


@dataclass
class RedisEventAdapter(IEventAdapter):
    """
    Redis Pub/Sub 事件适配器（P3-4）

    特性：
    - Redis PUBLISH/SUBSCRIBE 实现跨进程事件分发
    - 自动降级为内存模式（当 Redis 不可用时）
    - 保留内存订阅者（向后兼容 EventBusManager 的 subscribe API）
    - 每个 agent_id 独立的 Redis channel

    用法：
        adapter = RedisEventAdapter(redis_url="redis://localhost:6379/0")
        adapter.start()  # 启动后台订阅线程
        adapter.publish(event)
        adapter.stop()   # 停止后台线程
    """

    redis_url: str = "redis://localhost:6379/0"
    channel_prefix: str = REDIS_CHANNEL_PREFIX
    _redis_client: Any = field(default=None, repr=False)
    _pubsub: Any = field(default=None, repr=False)
    _subscriptions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    _memory_subscribers: Dict[str, List[Callable[[Event], None]]] = field(default_factory=lambda: defaultdict(list))
    _memory_global: List[Callable[[Event], None]] = field(default_factory=list)
    _started: bool = field(default=False)
    _stop_event: Optional[threading.Event] = field(default=None)
    _reader_thread: Optional[threading.Thread] = field(default=None)

    @property
    def trigger_mode(self) -> TriggerMode:
        return TriggerMode.SSE  # SSE is the closest semantic match for pub/sub

    # ---- 内存订阅 API（向后兼容）----

    def subscribe(self, agent_id: str, event_types: Optional[List[str]] = None) -> str:
        """订阅事件（返回 subscription_id）"""
        sub_id = str(uuid.uuid4())
        self._subscriptions[sub_id] = {
            "agent_id": agent_id,
            "event_types": set(event_types) if event_types else None,
        }
        logger.info(f"[RedisEventAdapter] Subscribed agent={agent_id}, sub={sub_id}")
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        """取消订阅"""
        self._subscriptions.pop(subscription_id, None)
        logger.info(f"[RedisEventAdapter] Unsubscribed sub={subscription_id}")

    def get_pending(self, agent_id: str, since: Optional[str] = None) -> List[Event]:
        """Redis 模式不支持 get_pending"""
        return []

    # ---- Redis 连接 ----

    def _get_redis_client(self):
        """获取或创建 Redis 客户端"""
        if self._redis_client is None:
            try:
                import redis
                self._redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=3,
                    socket_timeout=3,
                )
                # 测试连接
                self._redis_client.ping()
                logger.info(f"[RedisEventAdapter] Connected to {self.redis_url}")
            except Exception as e:
                logger.warning(f"[RedisEventAdapter] Redis not available: {e}. Falling back to memory mode.")
                self._redis_client = None
        return self._redis_client

    def _get_channel(self, agent_id: str) -> str:
        """获取 agent 对应的 channel 名"""
        return f"{self.channel_prefix}{agent_id}"

    # ---- 启动/停止 ----

    def start(self) -> None:
        """启动后台 Redis 订阅线程"""
        if self._started:
            return
        self._stop_event = threading.Event()
        self._started = True
        logger.info("[RedisEventAdapter] Starting background listener thread")
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

    def stop(self) -> None:
        """停止后台 Redis 订阅线程"""
        if not self._started:
            return
        self._stop_event.set()
        self._started = False
        if self._reader_thread:
            self._reader_thread.join(timeout=5)
        if self._pubsub:
            try:
                self._pubsub.close()
            except Exception:
                pass
        logger.info("[RedisEventAdapter] Stopped background listener thread")

    def _read_loop(self) -> None:
        """后台 Redis 订阅循环（独立线程）"""
        client = self._get_redis_client()
        if not client:
            return

        try:
            pubsub = client.pubsub()
            self._pubsub = pubsub

            # 订阅所有 agent channel 通配
            pattern = f"{self.channel_prefix}*"
            pubsub.psubscribe(pattern)
            logger.info(f"[RedisEventAdapter] Subscribed to pattern: {pattern}")

            for message in pubsub.listen():
                if self._stop_event and self._stop_event.is_set():
                    break
                if message["type"] not in ("pmessage", "message"):
                    continue

                try:
                    data = json.loads(message["data"])
                    event = Event.from_dict(data)
                    self._dispatch_to_subscribers(event)
                except Exception as e:
                    logger.error(f"[RedisEventAdapter] Error processing message: {e}")

        except Exception as e:
            logger.warning(f"[RedisEventAdapter] Redis read loop error: {e}")
            self._started = False

    def _dispatch_to_subscribers(self, event: Event) -> None:
        """将事件分发给内存订阅者"""
        # 通知类型订阅者
        for callback in self._memory_subscribers.get(event.event_type, []):
            try:
                callback(event)
            except Exception as e:
                logger.error(f"[RedisEventAdapter] Callback error: {e}")

        # 通知全局订阅者
        for callback in self._memory_global:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"[RedisEventAdapter] Global callback error: {e}")

    # ---- 发布 API ----

    def publish(self, event: Event) -> None:
        """
        发布事件：
        1. 通过 Redis channel 广播（跨进程）
        2. 同时分发给本地内存订阅者（向后兼容）
        """
        # 分发给本地订阅者（内存模式）
        self._dispatch_to_subscribers(event)

        # 通过 Redis 发布
        client = self._get_redis_client()
        if client:
            try:
                agent_id = event.agent_id or "global"
                channel = self._get_channel(agent_id)
                payload = json.dumps(event.to_dict(), default=str)
                client.publish(channel, payload)
                logger.debug(f"[RedisEventAdapter] Published to {channel}: {event.event_type}")
            except Exception as e:
                logger.warning(f"[RedisEventAdapter] Redis publish error: {e}")

    # ---- 统计 ----

    def get_stats(self) -> Dict[str, Any]:
        client_ok = False
        try:
            client = self._get_redis_client()
            client_ok = client is not None and client.ping()
        except Exception:
            pass

        return {
            "type": "redis",
            "redis_connected": client_ok,
            "redis_url": self.redis_url,
            "started": self._started,
            "memory_subscriptions": len(self._subscriptions),
            "memory_subscribers": {k: len(v) for k, v in self._memory_subscribers.items()},
            "memory_global_subscribers": len(self._memory_global),
        }


# ---- 便捷工厂函数 ----

def make_redis_adapter(
    redis_url: str = "redis://localhost:6379/0",
    channel_prefix: str = REDIS_CHANNEL_PREFIX,
    auto_start: bool = True,
) -> RedisEventAdapter:
    """
    创建 Redis EventAdapter 并可选启动

    用法：
        # 快速启动（自动 start）
        adapter = make_redis_adapter("redis://redis:6379/0")

        # 仅创建，稍后 start
        adapter = make_redis_adapter("redis://redis:6379/0", auto_start=False)
        # ... later ...
        adapter.start()
    """
    adapter = RedisEventAdapter(
        redis_url=redis_url,
        channel_prefix=channel_prefix,
    )
    if auto_start:
        adapter.start()
    return adapter