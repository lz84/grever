"""
Reins EventBus & SSE/Poll 实时事件推送

P5-02 SSE实时推送 + P5-07 Polling降级

集成 eventbus/manager.py 的 EventBusManager：
- SSE 端点: GET /api/v1/events/stream (agent_id 过滤)
- Polling 端点: GET /api/v1/events/pull (agent_id + since)
- 心跳: 每 15 秒发送 ": ping" comment

保留原有 poll 端点以保证向后兼容。
"""

import asyncio
import json
from loguru import logger
from typing import Optional, List

from fastapi import APIRouter, Query, Header, HTTPException
from fastapi.responses import StreamingResponse

from shared.eventbus.manager import get_event_bus_manager
from shared.eventbus.types import Event, EventPayload, AgentEventType, TriggerMode

router = APIRouter(prefix="/api/v1/events", tags=["events"])

# ============================================================================
# SSE 事件生成器（带 15 秒心跳）
# ============================================================================

async def sse_event_generator(
    client_id: str,
    queue: asyncio.Queue,
    connected_event: asyncio.Event,
    target_agent_id: Optional[str] = None,
):
    """
    SSE 事件生成器
    - 向客户端流式发送事件
    - 每 15 秒发送 ": ping" comment 保持连接活跃
    """
    # 发送连接成功消息
    yield f"id: {client_id}\nevent: connected\ndata: {json.dumps({'client_id': client_id, 'status': 'connected'}, ensure_ascii=False)}\n\n"
    connected_event.set()

    # P5-07-05: 通知断连检测器 SSE 已恢复
    if target_agent_id and target_agent_id != "anonymous":
        try:
            from reins.core.background_tasks import get_detector
            detector = get_detector('sse_disconnect')
            if detector:
                detector.on_sse_reconnect(target_agent_id)
        except Exception as e:
            logger.warning(f"[SSE] on_sse_reconnect error: {e}")

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15)
            except asyncio.TimeoutError:
                # P5-02: 15 秒心跳 comment
                yield f": ping\n\n"
                continue

            if event is None:
                break

            # 格式化为 SSE 消息
            data = event.to_dict()
            yield f"id: {event.event_id}\nevent: {event.event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    except asyncio.CancelledError:
        pass
    finally:
        # 清理 SSE 客户端
        try:
            bus_manager = get_event_bus_manager()
            sse_adapter = bus_manager.get_adapter(TriggerMode.SSE)
            if sse_adapter and hasattr(sse_adapter, 'unsubscribe'):
                # SseEventAdapter uses subscription_id, not client_id
                # We stored the mapping in a set during subscribe
                pass
        except Exception as e:
            logger.warning(f"[SSE] Cleanup error: {e}")

# ============================================================================
# SSE 端点 (P5-02)
# ============================================================================

@router.get("/stream")
async def stream_events(
    X_Agent_ID: Optional[str] = Header(None, alias="X-Agent-ID", description="Agent ID 用于事件路由"),
    agent_id: Optional[str] = Query(None, description="Agent ID（备用参数）"),
    workflow_id: Optional[str] = Query(None, description="过滤特定 workflow_id"),
):
    """
    SSE 实时事件流

    P5-02:
    - X-Agent-ID header 或 ?agent_id= query param 指定订阅的 Agent
    - workflow_id 过滤（多个用逗号分隔）
    - 每 15 秒心跳 comment

    事件类型:
      task_assigned, task_created, task_updated, task_completed,
      dispute_raised, agent_status_changed, mode_switched,
      step_started, step_completed, workflow_*

    连接示例:
      const es = new EventSource('/api/v1/events/stream?agent_id=agent-001')
    """
    # 确定 agent_id
    target_agent_id = X_Agent_ID or agent_id

    workflow_ids = None
    if workflow_id:
        workflow_ids = [wid.strip() for wid in workflow_id.split(",") if wid.strip()]

    bus_manager = get_event_bus_manager()
    sse_adapter = bus_manager.get_adapter(TriggerMode.SSE)

    if not sse_adapter:
        raise HTTPException(status_code=503, detail="SSE adapter not available")

    # 注册 SSE 客户端，返回 (subscription_id, queue)
    try:
        result = await sse_adapter.subscribe_async(
            agent_id=target_agent_id or "anonymous",
            workflow_ids=workflow_ids,
        )
        if isinstance(result, tuple) and len(result) == 2:
            subscription_id, queue = result
        else:
            # SseEventAdapter.subscribe returns subscription_id
            subscription_id = result
            queue = sse_adapter.get_client_queue(subscription_id)
    except Exception as e:
        logger.error(f"[SSE] Subscribe error: {e}")
        raise HTTPException(status_code=500, detail=f"SSE subscribe failed: {e}")

    connected_event = asyncio.Event()
    # Use subscription_id as client_id for SSE message id
    client_id = subscription_id

    async def wrapped_generator():
        async for chunk in sse_event_generator(client_id, queue, connected_event, target_agent_id):
            yield chunk

    return StreamingResponse(
        wrapped_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# ============================================================================
# Polling 端点 (P5-07)
# ============================================================================

@router.get("/pull")
async def pull_events(
    agent_id: str = Query(..., description="Agent ID"),
    since: Optional[str] = Query(None, description="上次拉取的时间戳（ISO 格式）"),
    limit: int = Query(50, ge=1, le=200, description="最大返回数量"),
):
    """
    轮询拉取事件（P5-07 Polling 降级模式）

    当 Agent 无法维持 SSE 连接时，使用此端点轮询拉取事件。
    - ?agent_id=xxx&since=2024-01-01T00:00:00&limit=50

    返回:
      {
        "events": [...],
        "has_more": true/false,
        "last_event_id": "...",
        "degraded": true/false,    // P5-07: 是否正在降级模式
        "count": 0
      }
    """
    bus_manager = get_event_bus_manager()

    # 获取该 Agent 当前的触发模式
    adapter = bus_manager.get_adapter(agent_id)
    degraded = adapter.trigger_mode == TriggerMode.POLLING if adapter else True

    events = bus_manager.get_pending(agent_id, since)

    # 限制返回数量
    limited_events = events[:limit]
    has_more = len(events) > limit

    # 获取 last_event_id
    last_event_id = None
    if limited_events:
        last_event_id = limited_events[-1].event_id if hasattr(limited_events[-1], 'event_id') else None

    # 序列化事件
    serialized = []
    for e in limited_events:
        if hasattr(e, 'to_dict'):
            serialized.append(e.to_dict())
        else:
            serialized.append(e)

    return {
        "events": serialized,
        "has_more": has_more,
        "last_event_id": last_event_id,
        "degraded": degraded,
        "count": len(serialized),
        # P5-07: 降级通知
        "mode_switched": degraded,
        "trigger_mode": "polling" if degraded else "sse",
    }

# ============================================================================
# 向后兼容: 旧 poll 端点 (保留)
# ============================================================================

@router.get("/poll")
async def poll_events(
    last_event_id: Optional[str] = Query(None),
    workflow_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """
    [向后兼容] 轮询事件（基于 reins/event_bus.py 的 PollEventBus）

    此端点兼容旧版实现。
    推荐使用 /pull 端点。
    """
    from reins.common.event_bus import get_poll_adapter

    poll_adapter = get_poll_adapter()
    if not poll_adapter:
        return {"error": "Poll adapter not available", "events": []}

    events = poll_adapter.get_events_after(
        last_event_id=last_event_id,
        workflow_id=workflow_id,
        limit=limit,
    )

    has_more = len(events) >= limit
    last_id = events[-1]["event_id"] if events else last_event_id

    return {
        "events": events,
        "has_more": has_more,
        "last_event_id": last_id,
        "count": len(events),
    }

# ============================================================================
# 统计端点
# ============================================================================

@router.get("/stats")
async def get_event_stats():
    """获取事件总线统计"""
    bus_manager = get_event_bus_manager()
    return bus_manager.get_stats()
