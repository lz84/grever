"""
EventBus Integration - P5-02 SSE 事件发布

提供 _publish_event 函数，用于在 reins API 中发布事件到 EventBus。
此模块不依赖 reins.api.server，避免循环导入。
"""

from loguru import logger

def _publish_event(event_type: str, agent_id: str = None, **payload_kwargs):
    """
    通过 EventBusManager 发布事件（P5-02）

    - event_type: 事件类型
    - agent_id: 关联的 Agent ID
    - **payload_kwargs: EventPayload 字段
    """
    try:
        # Import via module reference so patches can intercept the lookup
        from shared.eventbus.manager import get_event_bus_manager as _get_bus
        from shared.eventbus.types import Event, EventPayload

        payload = EventPayload(**payload_kwargs)
        event = Event(
            event_type=event_type,
            agent_id=agent_id,
            payload=payload,
        )
        bus = _get_bus()
        bus.publish(event)
    except Exception as e:
        logger.warning(f"[_publish_event] Warning: {e}")
