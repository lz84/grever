"""
EventBus 管理器（P5-01-05）

EventBusManager 实现：
- IEventBus 接口
- trigger_mode 驱动的 Adapter 切换
- 统一的 publish/subscribe/pending API
"""

import logging
import uuid
from typing import Any, Callable, Dict, List, Optional

from shared.eventbus.interfaces import IEventBus, IEventAdapter
from shared.eventbus.types import Event, TriggerMode
from shared.eventbus.store import EventStore
from shared.eventbus.sse_adapter import SseEventAdapter
from shared.eventbus.polling_adapter import PollingEventAdapter

logger = logging.getLogger(__name__)


# Agent 默认触发模式配置（可扩展为从 DB/Config 读取）
DEFAULT_TRIGGER_MODE: Dict[str, TriggerMode] = {}


class EventBusManager(IEventBus):
    """
    统一 EventBus 管理器（P5-01-05）

    核心功能：
    - 注册 SSE / Polling 两种 Adapter
    - 根据 Agent 的 trigger_mode 自动路由
    - 统一的事件发布接口
    - publish 时同时写入 DB（SSE 也走 DB 持久化）
    """

    def __init__(self, event_store: Optional[EventStore] = None):
        self._adapters: Dict[TriggerMode, IEventAdapter] = {}
        self._event_store = event_store or EventStore()
        self._subscriptions: Dict[str, Dict[str, Any]] = {}  # subscription_id → info

        # 注册默认 Adapter
        self.register_adapter(SseEventAdapter(event_store=self._event_store))
        self.register_adapter(PollingEventAdapter(event_store=self._event_store))

        # agent → trigger_mode 覆盖配置
        self._agent_modes: Dict[str, TriggerMode] = {}

        logger.info("[EventBusManager] Initialized with SSE + Polling adapters")

    @property
    def name(self) -> str:
        return "EventBusManager"

    # ---- Adapter 管理 ----

    def register_adapter(self, adapter: IEventAdapter) -> None:
        """注册一个 Adapter"""
        self._adapters[adapter.trigger_mode] = adapter
        logger.info(f"[EventBusManager] Registered adapter: {adapter.trigger_mode.value}")

    def get_adapter(self, agent_id_or_mode: str) -> IEventAdapter:
        if isinstance(agent_id_or_mode, TriggerMode):
            mode = agent_id_or_mode
            adapter = self._adapters.get(mode)
            if not adapter:
                logger.warning(f"[EventBusManager] Adapter for mode {mode} not found, falling back to polling")
                adapter = self._adapters.get(TriggerMode.POLLING)
            return adapter
        agent_id = agent_id_or_mode
        mode = self._agent_modes.get(
            agent_id,
            DEFAULT_TRIGGER_MODE.get(agent_id, TriggerMode.POLLING),
        )
        adapter = self._adapters.get(mode)
        if not adapter:
            logger.warning(f"[EventBusManager] Adapter for mode {mode} not found, falling back to polling")
            adapter = self._adapters.get(TriggerMode.POLLING)
        return adapter

    def set_agent_mode(self, agent_id: str, mode: TriggerMode) -> None:
        """设置 Agent 的触发模式（P5-01-05）"""
        self._agent_modes[agent_id] = mode
        logger.info(f"[EventBusManager] Agent {agent_id} trigger_mode → {mode.value}")

    # ---- IEventBus 实现 ----

    def subscribe(
        self,
        agent_id: str,
        event_types: Optional[List[str]] = None,
        trigger_mode: Optional[TriggerMode] = None,
    ) -> str:
        """
        订阅事件（P5-01-01）

        - agent_id: Agent ID
        - event_types: 感兴趣的事件类型
        - trigger_mode: 指定触发模式，None 表示自动选择
        """
        if trigger_mode is None:
            trigger_mode = self._agent_modes.get(
                agent_id,
                DEFAULT_TRIGGER_MODE.get(agent_id, TriggerMode.POLLING),
            )

        adapter = self._adapters.get(trigger_mode)
        if not adapter:
            adapter = self._adapters[TriggerMode.POLLING]
            logger.warning(f"[EventBusManager] Mode {trigger_mode} not available, using polling")

        subscription_id = adapter.subscribe(agent_id, event_types)
        self._subscriptions[subscription_id] = {
            "agent_id": agent_id,
            "trigger_mode": trigger_mode,
            "event_types": event_types,
        }

        logger.info(f"[EventBusManager] Subscribed agent={agent_id}, mode={trigger_mode.value}, sub={subscription_id}")
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> None:
        """取消订阅"""
        info = self._subscriptions.pop(subscription_id, None)
        if not info:
            logger.warning(f"[EventBusManager] Unknown subscription: {subscription_id}")
            return

        adapter = self._adapters.get(info["trigger_mode"])
        if adapter:
            adapter.unsubscribe(subscription_id)

        logger.info(f"[EventBusManager] Unsubscribed {subscription_id}")

    def publish(self, event: Event) -> None:
        """
        发布事件（P5-01-01）

        流程：
        1. 持久化到 DB（EventStore）
        2. 推送给 SSE Adapter（实时推送）
        3. 通知 Polling Adapter（更新 buffer）
        """
        # 持久化到 DB
        self._event_store.save(event)

        # 推送给所有 Adapter
        for mode, adapter in self._adapters.items():
            try:
                adapter.publish(event)
            except Exception as e:
                logger.error(f"[EventBusManager] Adapter {mode.value} publish error: {e}")

    def get_pending(self, agent_id: str, since: Optional[str] = None) -> List[Event]:
        """
        获取 Agent 的待处理事件（统一接口）
        """
        adapter = self.get_adapter(agent_id)
        if hasattr(adapter, "get_pending"):
            return adapter.get_pending(agent_id, since)
        return []

    def get_stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "adapters": {mode.value: a.get_stats() for mode, a in self._adapters.items()},
            "agent_modes": {aid: m.value for aid, m in self._agent_modes.items()},
            "active_subscriptions": len(self._subscriptions),
        }


# ============================================================================
# 全局单例
# ============================================================================

_manager: Optional[EventBusManager] = None


def get_event_bus_manager() -> EventBusManager:
    """获取全局 EventBusManager 单例"""
    global _manager
    if _manager is None:
        _manager = EventBusManager()
    return _manager


def reset_event_bus_manager() -> None:
    """重置全局管理器（主要用于测试）"""
    global _manager
    _manager = None
