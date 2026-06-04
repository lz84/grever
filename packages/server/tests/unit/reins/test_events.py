"""
Events Module Tests

测试：
- EventBus: 订阅/发布/SSE客户端管理
- SSE端点: /api/v1/events/stream
- make_tracker_callback: WorkflowExecutionEngine事件转发
"""

import asyncio
import pytest
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

# 添加 src 到路径
src_dir = str(Path(__file__).parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from reins.common.events import router as events_router
from reins.common.event_bus import (
    EventBus, EventType, WorkflowEvent,
    get_event_bus, make_tracker_callback,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# EventBus Tests
# ============================================================================

class TestEventBus:
    """EventBus 单例测试"""

    def test_singleton(self):
        """测试单例模式"""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2
        logger.info("✓ EventBus is singleton")

    def test_initial_state(self):
        """测试初始状态"""
        bus = get_event_bus()
        stats = bus.get_stats()
        assert stats["active_clients"] == 0
        assert len(stats["subscribers"]) == 0
        assert stats["global_subscribers"] == 0
        logger.info("✓ Initial state correct")

    def test_subscribe_unsubscribe(self):
        """测试订阅/取消订阅"""
        bus = get_event_bus()
        received = []

        def callback(event: WorkflowEvent):
            received.append(event)

        # 订阅
        unsubscribe = bus.subscribe("step_started", callback)
        callbacks = bus._subscribers.get("step_started", [])
        assert callback in callbacks
        logger.info("✓ Subscribe works")

        # 取消订阅
        unsubscribe()
        callbacks = bus._subscribers.get("step_started", [])
        assert callback not in callbacks
        logger.info("✓ Unsubscribe works")

    @pytest.mark.asyncio
    async def test_publish_single_subscriber(self):
        """测试发布到单个订阅者"""
        bus = get_event_bus()
        received = []

        def callback(event: WorkflowEvent):
            received.append(event)

        # Mock _push_to_sse_clients to avoid event loop issues
        with patch.object(bus, '_push_to_sse_clients', new_callable=AsyncMock):
            bus.subscribe("workflow_started", callback)
            bus.emit("workflow_started", "wf-001", "", {"key": "value"})

            assert len(received) == 1
            assert received[0].workflow_id == "wf-001"
            assert received[0].event_type == "workflow_started"
            logger.info("✓ Publish to single subscriber works")

    @pytest.mark.asyncio
    async def test_emit_convenience(self):
        """测试 emit 便捷方法"""
        bus = get_event_bus()
        received = []

        def callback(event: WorkflowEvent):
            received.append(event)

        with patch.object(bus, '_push_to_sse_clients', new_callable=AsyncMock):
            bus.subscribe("step_completed", callback)
            bus.emit("step_completed", "wf-001", "step-001", {"result": "ok"})

            assert len(received) == 1
            assert received[0].step_id == "step-001"
            assert received[0].data["result"] == "ok"
            logger.info("✓ emit convenience method works")

    @pytest.mark.asyncio
    async def test_global_subscribe(self):
        """测试全局订阅"""
        bus = get_event_bus()
        received = []

        def callback(event: WorkflowEvent):
            received.append(event)

        with patch.object(bus, '_push_to_sse_clients', new_callable=AsyncMock):
            bus.subscribe_global(callback)
            bus.emit("any_event_type", "wf-001")

            assert len(received) == 1
            logger.info("✓ Global subscribe works")

    def test_workflow_event_to_sse_data(self):
        """测试事件序列化"""
        event = WorkflowEvent(
            event_type="step_started",
            workflow_id="wf-001",
            step_id="step-001",
            data={"agent_id": "agent-001"},
        )

        sse_data = event.to_sse_data()
        assert sse_data["event_type"] == "step_started"
        assert sse_data["workflow_id"] == "wf-001"
        assert sse_data["step_id"] == "step-001"
        assert sse_data["data"]["agent_id"] == "agent-001"
        assert "event_id" in sse_data
        assert "timestamp" in sse_data
        logger.info("✓ WorkflowEvent serialization works")

    def test_workflow_event_to_sse_message(self):
        """测试 SSE 消息格式"""
        event = WorkflowEvent(
            event_type="step_completed",
            workflow_id="wf-001",
            step_id="step-001",
            data={"status": "success"},
        )

        msg = event.to_sse_message()
        assert "id:" in msg
        assert "event: step_completed" in msg
        assert '"workflow_id": "wf-001"' in msg
        assert "\n\n" in msg  # SSE message separator
        logger.info("✓ SSE message format correct")


class TestEventBusSSE:
    """EventBus SSE 客户端测试"""

    @pytest.mark.asyncio
    async def test_subscribe_sse(self):
        """测试 SSE 客户端注册"""
        bus = get_event_bus()
        client_id, queue = await bus.subscribe_sse()

        assert client_id is not None
        assert isinstance(queue, asyncio.Queue)
        assert bus.get_client_count() == 1
        logger.info(f"✓ SSE client registered: {client_id}")

        await bus.unsubscribe_sse(client_id)
        assert bus.get_client_count() == 0
        logger.info("✓ SSE client unregistered")

    @pytest.mark.asyncio
    async def test_sse_workflow_filter(self):
        """测试 SSE workflow 过滤"""
        bus = get_event_bus()
        client_id, queue = await bus.subscribe_sse(workflow_ids=["wf-001", "wf-002"])

        # 发布到 wf-001
        event1 = WorkflowEvent("step_started", "wf-001", "step-1")
        bus.publish(event1)

        # 发布到 wf-003（应该被过滤）
        event2 = WorkflowEvent("step_started", "wf-003", "step-2")
        bus.publish(event2)

        # 只有 wf-001 的事件应该到达
        received = []
        for _ in range(2):
            try:
                ev = await asyncio.wait_for(queue.get(), timeout=0.5)
                received.append(ev)
            except asyncio.TimeoutError:
                break

        assert len(received) == 1
        assert received[0].workflow_id == "wf-001"
        logger.info("✓ SSE workflow filter works")

        await bus.unsubscribe_sse(client_id)


# ============================================================================
# make_tracker_callback Tests
# ============================================================================

class TestMakeTrackerCallback:
    """make_tracker_callback 测试"""

    @pytest.mark.asyncio
    async def test_callback_step_started(self):
        """测试 step_started 事件映射"""
        bus = get_event_bus()
        received = []

        def callback(event: WorkflowEvent):
            received.append(event)

        with patch.object(bus, '_push_to_sse_clients', new_callable=AsyncMock):
            bus.subscribe_global(callback)

            tracker_callback = make_tracker_callback(bus)
            tracker_callback({
                "event_type": "step_started",
                "workflow_id": "wf-001",
                "step_id": "step-001",
                "data": {"agent_id": "agent-001"},
            })

            assert len(received) == 1
            assert received[0].event_type == EventType.STEP_STARTED.value
            assert received[0].workflow_id == "wf-001"
            logger.info("✓ step_started event mapping works")

    @pytest.mark.asyncio
    async def test_callback_workflow_completed(self):
        """测试 workflow_completed 事件映射"""
        bus = get_event_bus()
        received = []

        def callback(event: WorkflowEvent):
            received.append(event)

        with patch.object(bus, '_push_to_sse_clients', new_callable=AsyncMock):
            bus.subscribe_global(callback)

            tracker_callback = make_tracker_callback(bus)
            tracker_callback({
                "event_type": "workflow_completed",
                "workflow_id": "wf-001",
                "step_id": "",
                "data": {"total_steps": 5},
            })

            assert len(received) == 1
            assert received[0].event_type == EventType.WORKFLOW_COMPLETED.value
            logger.info("✓ workflow_completed event mapping works")

    @pytest.mark.asyncio
    async def test_callback_workflow_error(self):
        """测试 workflow_error -> workflow_failed 映射"""
        bus = get_event_bus()
        received = []

        def callback(event: WorkflowEvent):
            received.append(event)

        with patch.object(bus, '_push_to_sse_clients', new_callable=AsyncMock):
            bus.subscribe_global(callback)

            tracker_callback = make_tracker_callback(bus)
            tracker_callback({
                "event_type": "workflow_error",
                "workflow_id": "wf-001",
                "step_id": "",
                "data": {"error": "some error"},
            })

            assert len(received) == 1
            assert received[0].event_type == EventType.WORKFLOW_FAILED.value
            logger.info("✓ workflow_error -> workflow_failed mapping works")

    @pytest.mark.asyncio
    async def test_callback_step_cancelled(self):
        """测试 step_cancelled -> step_failed 映射"""
        bus = get_event_bus()
        received = []

        def callback(event: WorkflowEvent):
            received.append(event)

        with patch.object(bus, '_push_to_sse_clients', new_callable=AsyncMock):
            bus.subscribe_global(callback)

            tracker_callback = make_tracker_callback(bus)
            tracker_callback({
                "event_type": "step_cancelled",
                "workflow_id": "wf-001",
                "step_id": "step-001",
                "data": {},
            })

            assert len(received) == 1
            assert received[0].event_type == EventType.STEP_FAILED.value
            logger.info("✓ step_cancelled -> step_failed mapping works")

    @pytest.mark.asyncio
    async def test_callback_unknown_event(self):
        """测试未知事件类型透传"""
        bus = get_event_bus()
        received = []

        def callback(event: WorkflowEvent):
            received.append(event)

        with patch.object(bus, '_push_to_sse_clients', new_callable=AsyncMock):
            bus.subscribe_global(callback)

            tracker_callback = make_tracker_callback(bus)
            tracker_callback({
                "event_type": "custom_event",
                "workflow_id": "wf-001",
                "step_id": "step-001",
                "data": {"custom": "data"},
            })

            assert len(received) == 1
            assert received[0].event_type == "custom_event"
            logger.info("✓ Unknown event type passes through")


# ============================================================================
# Integration Test
# ============================================================================

class TestEventBusIntegration:
    """EventBus 集成测试"""

    @pytest.mark.asyncio
    async def test_full_event_flow(self):
        """完整事件流测试"""
        bus = get_event_bus()

        # 1. 注册 SSE 客户端
        client_id, queue = await bus.subscribe_sse(workflow_ids=["wf-integration"])

        # 2. 订阅特定事件
        step_events = []
        def step_callback(event: WorkflowEvent):
            step_events.append(event)
        bus.subscribe("step_started", step_callback)
        bus.subscribe("step_completed", step_callback)

        # 3. 发布工作流开始事件
        bus.emit("workflow_started", "wf-integration", "", {"total_steps": 3})

        # 4. 发布步骤事件
        bus.emit("step_started", "wf-integration", "step-001", {"name": "Step 1"})
        bus.emit("step_completed", "wf-integration", "step-001", {"result": "ok"})
        bus.emit("step_started", "wf-integration", "step-002", {"name": "Step 2"})
        bus.emit("step_completed", "wf-integration", "step-002", {"result": "ok"})

        # 5. 发布工作流完成事件
        bus.emit("workflow_completed", "wf-integration", "", {"completed": 2})

        # 6. 等待事件到达 SSE 队列
        sse_events = []
        for _ in range(6):
            try:
                ev = await asyncio.wait_for(queue.get(), timeout=1.0)
                sse_events.append(ev)
            except asyncio.TimeoutError:
                break

        # 验证
        assert len(sse_events) >= 4  # workflow_started + 4 step events + workflow_completed
        assert len(step_events) == 4  # 2 step_started + 2 step_completed

        # SSE 应包含 workflow 级别事件（因为过滤了 wf-integration）
        wf_events = [e for e in sse_events if e.workflow_id == "wf-integration"]
        assert len(wf_events) >= 4

        logger.info(f"✓ Full event flow: {len(sse_events)} SSE events, {len(step_events)} step events")

        # 清理
        await bus.unsubscribe_sse(client_id)

    def test_stats(self):
        """测试统计信息"""
        bus = get_event_bus()
        stats = bus.get_stats()
        assert "active_clients" in stats
        assert "subscribers" in stats
        assert "global_subscribers" in stats
        logger.info(f"✓ Stats: {stats}")


# ============================================================================
# SSE Endpoint Tests
# ============================================================================

class TestSSEEndpoint:
    """SSE 端点测试"""

    def test_events_router_exists(self):
        """测试 events router 存在"""
        assert events_router is not None
        assert events_router.prefix == "/api/v1/events"
        logger.info("✓ Events router exists with correct prefix")

    def test_events_router_routes(self):
        """测试 events router 包含正确路由"""
        routes = [route.path for route in events_router.routes]
        # Routes include full path like /api/v1/events/stream
        assert any("stream" in r for r in routes), f"stream not in {routes}"
        assert any("stats" in r for r in routes), f"stats not in {routes}"
        logger.info(f"✓ Events router routes: {routes}")


# ============================================================================
# Main Test
# ============================================================================

async def run_all_tests():
    """运行所有测试"""
    logger.info("\n" + "=" * 60)
    logger.info("Events Module Test Suite")
    logger.info("=" * 60 + "\n")

    try:
        # Singleton & State tests
        test_singleton()
        test_initial_state()

        # Subscribe/Publish tests
        test_subscribe_unsubscribe()
        await test_publish_single_subscriber()
        await test_emit_convenience()
        await test_global_subscribe()
        test_workflow_event_to_sse_data()
        test_workflow_event_to_sse_message()

        # SSE tests
        await test_subscribe_sse()
        await test_sse_workflow_filter()

        # Callback tests
        await test_callback_step_started()
        await test_callback_workflow_completed()
        await test_callback_workflow_error()
        await test_callback_step_cancelled()
        await test_callback_unknown_event()

        # Integration tests
        await test_full_event_flow()
        test_stats()

        # Endpoint tests
        test_events_router_exists()
        test_events_router_routes()

        logger.info("\n" + "=" * 60)
        logger.info("✓ All events tests passed!")
        logger.info("=" * 60 + "\n")

    except Exception as e:
        logger.error(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(run_all_tests())
