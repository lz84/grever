"""
EventBus 接口定义（P5-01-01）

定义：
- IEventAdapter: 事件适配器接口（SSE / Polling / Callback）
- IEventBus: 统一事件总线接口
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from shared.eventbus.types import Event, TriggerMode


class IEventAdapter(ABC):
    """
    事件适配器接口（P5-01-01）

    定义三种 Adapter 必须实现的方法：
    - subscribe: 订阅特定 agent 的事件
    - unsubscribe: 取消订阅
    - get_pending: 获取待处理事件（轮询模式）
    - push: 推送事件（推送模式）
    """

    @property
    @abstractmethod
    def trigger_mode(self) -> TriggerMode:
        """返回适配器的触发模式"""
        pass

    @abstractmethod
    def subscribe(self, agent_id: str, event_types: Optional[List[str]] = None) -> str:
        """
        订阅事件
        - agent_id: 订阅的 Agent ID
        - event_types: 感兴趣的事件类型列表，None 表示全部
        返回 subscription_id
        """
        pass

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> None:
        """
        取消订阅
        - subscription_id: 订阅 ID
        """
        pass

    @abstractmethod
    def get_pending(self, agent_id: str, since: Optional[str] = None) -> List[Event]:
        """
        获取待处理事件（轮询适配器）
        - agent_id: Agent ID
        - since: 上次获取事件的 timestamp，None 表示从头
        返回未读事件列表
        """
        pass

    @abstractmethod
    def publish(self, event: Event) -> None:
        """
        发布事件（推送适配器）
        - event: 事件对象
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """获取适配器统计信息"""
        pass


class IEventBus(ABC):
    """
    统一事件总线接口（P5-01-01）

    定义：
    - subscribe / unsubscribe: Agent 订阅事件
    - publish: 发布事件
    - get_pending: 获取待处理事件（统一接口，路由到对应 Adapter）
    - get_adapter: 获取特定 Agent 使用的 Adapter
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """总线名称"""
        pass

    @abstractmethod
    def subscribe(
        self,
        agent_id: str,
        event_types: Optional[List[str]] = None,
        trigger_mode: Optional[TriggerMode] = None,
    ) -> str:
        """
        订阅事件
        - agent_id: Agent ID
        - event_types: 感兴趣的事件类型列表
        - trigger_mode: 触发模式（None 表示使用 Agent 默认模式）
        返回 subscription_id
        """
        pass

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> None:
        """取消订阅"""
        pass

    @abstractmethod
    def publish(self, event: Event) -> None:
        """发布事件到所有订阅者"""
        pass

    @abstractmethod
    def get_pending(self, agent_id: str, since: Optional[str] = None) -> List[Event]:
        """
        获取 Agent 的待处理事件
        - agent_id: Agent ID
        - since: 上次获取的时间戳
        """
        pass

    @abstractmethod
    def get_adapter(self, agent_id: str) -> IEventAdapter:
        """
        获取 Agent 对应的 Adapter
        - agent_id: Agent ID
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """获取总线统计信息"""
        pass
