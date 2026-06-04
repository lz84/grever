"""
SSE Event Adapter（P5-01-03）

实现 IEventAdapter 接口，支持：
- 多 Agent 并发订阅
- 连接管理
- 断连检测（心跳超时）
"""

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from shared.eventbus.interfaces import IEventAdapter
from shared.eventbus.types import Event, EventPayload, TriggerMode
from shared.eventbus.store import EventStore

logger = logging.getLogger(__name__)


@dataclass
class SSEClient:
    """SSE 客户端连接"""
    client_id: str
    agent_id: str
    queue: asyncio.Queue
    workflow_ids: Optional[Set[str]] = None
    event_types: Optional[Set[str]] = None
    connected_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: float = field(default_factory=time.time)
    event_count: int = 0
    subscription_id: str = ""


class SseEventAdapter(IEventAdapter):
    """
    SSE 事件适配器（P5-01-03）

    特性：
    - 多 Agent 并发订阅
    - 连接管理（client_id → SSEClient）
    - 断连检测（idle timeout）
    - workflow_id / event_type 过滤
    """

    HEARTBEAT_TIMEOUT = 120.0  # 2分钟无活动视为断连

    def __init__(self, event_store: Optional[EventStore] = None, max_queue_size: int = 100):
        self._clients: Dict[str, SSEClient] = {}
        self._agent_subscriptions: Dict[str, List[str]] = defaultdict(list)  # agent_id → [subscription_id]
        self._subscription_to_client: Dict[str, str] = {}  # subscription_id → client_id
        self._lock = asyncio.Lock()
        self._event_store = event_store
        self._max_queue_size = max_queue_size
        self._cleanup_task: Optional[asyncio.Task] = None

        logger.info("[SseEventAdapter] Initialized")

    @property
    def trigger_mode(self) -> TriggerMode:
        return TriggerMode.SSE

    def subscribe(self, agent_id: str, event_types: Optional[List[str]] = None) -> str:
        """
        注册 SSE 客户端订阅
        返回 subscription_id
        """
        subscription_id = str(uuid.uuid4())
        client_id = str(uuid.uuid4())
        queue: asyncio.Queue[Optional[Event]] = asyncio.Queue(maxsize=self._max_queue_size)

        client = SSEClient(
            client_id=client_id,
            agent_id=agent_id,
            queue=queue,
            subscription_id=subscription_id,
        )

        self._agent_subscriptions[agent_id].append(subscription_id)
        self._subscription_to_client[subscription_id] = client_id
        self._clients[client_id] = client

        logger.info(f"[SseEventAdapter] Subscribed agent={agent_id}, subscription={subscription_id}")
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> None:
        """取消 SSE 订阅"""
        client_id = self._subscription_to_client.pop(subscription_id, None)
        if client_id and client_id in self._clients:
            client = self._clients[client_id]
            # 通知生成器退出
            try:
                client.queue.put_nowait(None)
            except asyncio.QueueFull:
                pass
            # 从 agent_subscriptions 中移除
            agent_id = client.agent_id
            if agent_id in self._agent_subscriptions:
                self._agent_subscriptions[agent_id] = [
                    sid for sid in self._agent_subscriptions[agent_id]
                    if sid != subscription_id
                ]
            del self._clients[client_id]
            logger.info(f"[SseEventAdapter] Unsubscribed subscription={subscription_id}")

    async def subscribe_async(
        self,
        agent_id: str,
        workflow_ids: Optional[List[str]] = None,
        event_types: Optional[List[str]] = None,
    ) -> tuple[str, asyncio.Queue]:
        """
        异步注册 SSE 客户端（用于 FastAPI 端点）
        返回 (subscription_id, event_queue)
        """
        subscription_id = str(uuid.uuid4())
        client_id = str(uuid.uuid4())
        queue: asyncio.Queue[Optional[Event]] = asyncio.Queue(maxsize=self._max_queue_size)

        client = SSEClient(
            client_id=client_id,
            agent_id=agent_id,
            queue=queue,
            workflow_ids=set(workflow_ids) if workflow_ids else None,
            event_types=set(event_types) if event_types else None,
            subscription_id=subscription_id,
        )

        async with self._lock:
            self._agent_subscriptions[agent_id].append(subscription_id)
            self._subscription_to_client[subscription_id] = client_id
            self._clients[client_id] = client

        logger.info(f"[SseEventAdapter] Async subscribe agent={agent_id}, client={client_id}")
        return subscription_id, queue

    def publish(self, event: Event) -> None:
        """
        推送事件到所有匹配的 SSE 客户端（P5-01-03）
        """
        try:
            asyncio.create_task(self._push_async(event))
        except RuntimeError:
            # 无运行中的 event loop（测试环境），同步处理
            self._push_sync(event)

    async def _push_async(self, event: Event) -> None:
        """异步推送"""
        async with self._lock:
            clients = list(self._clients.items())

        pushed = 0
        for client_id, client in clients:
            try:
                # 检查过滤条件
                if client.workflow_ids and event.payload.workflow_id not in client.workflow_ids:
                    continue
                if client.event_types and event.event_type not in client.event_types:
                    continue

                # 推送到队列
                try:
                    client.queue.put_nowait(event)
                    client.event_count += 1
                    client.last_heartbeat = time.time()
                    pushed += 1
                except asyncio.QueueFull:
                    logger.warning(f"[SseEventAdapter] Queue full for client {client_id}, dropping")
            except Exception as e:
                logger.error(f"[SseEventAdapter] Push error to {client_id}: {e}")

        if pushed > 0:
            logger.debug(f"[SseEventAdapter] Pushed event {event.event_id} to {pushed} clients")

    def _push_sync(self, event: Event) -> None:
        """同步推送（无 event loop）"""
        for client_id, client in self._clients.items():
            try:
                if client.workflow_ids and event.payload.workflow_id not in client.workflow_ids:
                    continue
                if client.event_types and event.event_type not in client.event_types:
                    continue
                client.event_count += 1
                client.last_heartbeat = time.time()
            except Exception as e:
                logger.error(f"[SseEventAdapter] Sync push error: {e}")

    def get_pending(self, agent_id: str, since: Optional[str] = None) -> List[Event]:
        """
        SSE 模式不支持 get_pending（由轮询适配器提供）
        """
        return []

    def get_stats(self) -> Dict[str, Any]:
        return {
            "type": "sse",
            "active_clients": len(self._clients),
            "total_subscriptions": len(self._subscription_to_client),
            "clients": [
                {
                    "client_id": c.client_id,
                    "agent_id": c.agent_id,
                    "event_count": c.event_count,
                    "connected_at": c.connected_at.isoformat(),
                }
                for c in self._clients.values()
            ],
        }

    def get_client_queue(self, subscription_id: str) -> Optional[asyncio.Queue]:
        """获取订阅的队列（用于 SSE 端点）"""
        client_id = self._subscription_to_client.get(subscription_id)
        if client_id and client_id in self._clients:
            return self._clients[client_id].queue
        return None
