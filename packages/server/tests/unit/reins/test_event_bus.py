"""
EventBus 抽象层单元测试

测试覆盖：
- 抽象接口定义
- SSE adapter 注册/推送/取消注册
- Poll adapter 发布/增量拉取/TTL过期
- Unified router 多 adapter 同步
- make_tracker_callback 兼容性
- 向后兼容（get_event_bus 返回正确类型）
"""

import asyncio
import time
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from reins.common.event_bus import (
    EventBus,
    EventType,
    PollEventBus,
    SSEEventBus,
    UnifiedEventBus,
    WorkflowEvent,
    get_event_bus,
    get_poll_adapter,
    get_sse_adapter,
    make_tracker_callback,
    reset_event_bus,
)


# ============================================================================
# 辅助函数
# ============================================================================

def make_event(event_type="test_event", workflow_id="wf-1", step_id="step-1", data=None, event_id=None):
    """创建测试事件"""
    return WorkflowEvent(
        event_type=event_type,
        workflow_id=workflow_id,
        step_id=step_id,
        data=data or {},
        event_id=event_id or str(uuid.uuid4()),
    )


# ============================================================================
# WorkflowEvent 测试
# ============================================================================

class TestWorkflowEvent:
    """WorkflowEvent 数据模型测试"""

    def test_creation(self):
        event = make_event()
        assert event.event_type == "test_event"
        assert event.workflow_id == "wf-1"
        assert event.step_id == "step-1"
        assert event.event_id  # 自动生成
        assert event.timestamp  # 自动生成

    def test_to_sse_data(self):
        event = make_event(data={"key": "value"})
        data = event.to_sse_data()
        assert data["event_type"] == "test_event"
        assert data["data"] == {"key": "value"}

    def test_to_sse_message(self):
        event = make_event(event_type="step_completed")
        msg = event.to_sse_message()
        assert f"event: step_completed" in msg
        assert f"id: {event.event_id}" in msg
        assert "data:" in msg

    def test_to_dict(self):
        event = make_event()
        d = event.to_dict()
        assert isinstance(d, dict)
        assert d["event_type"] == "test_event"


# ============================================================================
# SSEEventBus 测试
# ============================================================================

class TestSSEEventBus:
    """SSE Event Bus Adapter 测试"""

    def setup_method(self):
        self.bus = SSEEventBus()

    def test_subscribe_and_publish(self):
        """测试订阅和发布"""
        callback = MagicMock()
        unsubscribe = self.bus.subscribe("test_event", callback)

        event = make_event(event_type="test_event")
        self.bus.publish(event)

        callback.assert_called_once_with(event)

    def test_unsubscribe(self):
        """测试取消订阅"""
        callback = MagicMock()
        unsubscribe = self.bus.subscribe("test_event", callback)
        unsubscribe()

        event = make_event(event_type="test_event")
        self.bus.publish(event)

        callback.assert_not_called()

    def test_subscribe_global(self):
        """测试全局订阅"""
        callback = MagicMock()
        self.bus.subscribe_global(callback)

        event = make_event(event_type="any_event")
        self.bus.publish(event)

        callback.assert_called_once_with(event)

    def test_emit_convenience(self):
        """测试便捷发布"""
        callback = MagicMock()
        self.bus.subscribe("step_started", callback)

        self.bus.emit("step_started", "wf-1", step_id="s1", data={"agent": "test"})

        assert callback.call_count == 1
        event = callback.call_args[0][0]
        assert event.event_type == "step_started"
        assert event.workflow_id == "wf-1"
        assert event.step_id == "s1"
        assert event.data == {"agent": "test"}

    def test_publish_wrong_event_type(self):
        """测试只通知匹配的订阅者"""
        cb1 = MagicMock()
        cb2 = MagicMock()
        self.bus.subscribe("event_a", cb1)
        self.bus.subscribe("event_b", cb2)

        self.bus.emit("event_a", "wf-1")

        cb1.assert_called_once()
        cb2.assert_not_called()

    def test_get_stats(self):
        """测试统计信息"""
        self.bus.subscribe("test", MagicMock())
        self.bus.subscribe_global(MagicMock())

        stats = self.bus.get_stats()
        assert stats["type"] == "sse"
        assert stats["global_subscribers"] == 1
        assert "test" in stats["subscribers"]

    @pytest.mark.asyncio
    async def test_sse_client_register_unregister(self):
        """测试 SSE 客户端注册和注销"""
        client_id, queue = await self.bus.subscribe_sse()
        assert client_id
        assert isinstance(queue, asyncio.Queue)
        assert self.bus.get_client_count() == 1

        await self.bus.unsubscribe_sse(client_id)
        assert self.bus.get_client_count() == 0

    @pytest.mark.asyncio
    async def test_sse_push_to_clients(self):
        """测试事件推送到 SSE 客户端"""
        client_id, queue = await self.bus.subscribe_sse()

        event = make_event()
        await self.bus._push_to_sse_clients(event)

        received = queue.get_nowait()
        assert received.event_id == event.event_id


# ============================================================================
# PollEventBus 测试
# ============================================================================

class TestPollEventBus:
    """Poll Event Bus Adapter 测试"""

    def setup_method(self):
        self.bus = PollEventBus(max_events=10, ttl_seconds=300.0)

    def test_publish_and_get_all(self):
        """测试发布和获取全部事件"""
        self.bus.emit("event_a", "wf-1")
        self.bus.emit("event_b", "wf-1")
        self.bus.emit("event_c", "wf-1")

        events = self.bus.get_events_after()
        assert len(events) == 3
        assert events[0]["event_type"] == "event_a"

    def test_incremental_pull(self):
        """测试增量拉取"""
        e1 = make_event(event_type="e1", event_id="id-1")
        e2 = make_event(event_type="e2", event_id="id-2")
        e3 = make_event(event_type="e3", event_id="id-3")

        self.bus.publish(e1)
        self.bus.publish(e2)
        self.bus.publish(e3)

        # 拉取 id-1 之后的事件
        events = self.bus.get_events_after(last_event_id="id-1")
        assert len(events) == 2
        assert events[0]["event_type"] == "e2"
        assert events[1]["event_type"] == "e3"

    def test_incremental_pull_from_middle(self):
        """测试从中间位置增量拉取"""
        for i in range(5):
            self.bus.publish(make_event(event_type=f"e{i}", event_id=f"id-{i}"))

        events = self.bus.get_events_after(last_event_id="id-2")
        assert len(events) == 2  # id-3, id-4
        assert events[0]["event_type"] == "e3"

    def test_workflow_id_filter(self):
        """测试 workflow_id 过滤"""
        self.bus.publish(make_event(event_type="e1", workflow_id="wf-a"))
        self.bus.publish(make_event(event_type="e2", workflow_id="wf-b"))
        self.bus.publish(make_event(event_type="e3", workflow_id="wf-a"))

        events = self.bus.get_events_after(workflow_id="wf-a")
        assert len(events) == 2
        assert all(e["workflow_id"] == "wf-a" for e in events)

    def test_limit(self):
        """测试 limit 限制"""
        for i in range(10):
            self.bus.publish(make_event(event_type=f"e{i}"))

        events = self.bus.get_events_after(limit=3)
        assert len(events) == 3

    def test_max_events_buffer(self):
        """测试 buffer 大小限制"""
        bus = PollEventBus(max_events=3)
        for i in range(10):
            bus.publish(make_event(event_type=f"e{i}"))

        events = bus.get_events_after()
        assert len(events) == 3
        # 应该保留最后 3 个
        assert events[0]["event_type"] == "e7"
        assert events[2]["event_type"] == "e9"

    def test_ttl_expiration(self):
        """测试 TTL 过期清理"""
        bus = PollEventBus(max_events=100, ttl_seconds=0.001)  # 1ms TTL

        bus.publish(make_event(event_type="old"))
        time.sleep(0.01)  # 等待过期

        bus.publish(make_event(event_type="new"))

        events = bus.get_events_after()
        # old 事件应该已过期
        event_types = [e["event_type"] for e in events]
        assert "old" not in event_types
        assert "new" in event_types

    def test_subscribe_and_publish(self):
        """测试订阅回调"""
        callback = MagicMock()
        self.bus.subscribe("test_event", callback)

        event = make_event(event_type="test_event")
        self.bus.publish(event)

        callback.assert_called_once_with(event)

    def test_get_stats(self):
        """测试统计信息"""
        self.bus.publish(make_event())
        self.bus.publish(make_event())

        stats = self.bus.get_stats()
        assert stats["type"] == "poll"
        assert stats["buffer_size"] == 2
        assert stats["max_events"] == 10


# ============================================================================
# UnifiedEventBus 测试
# ============================================================================

class TestUnifiedEventBus:
    """Unified Event Bus Router 测试"""

    def setup_method(self):
        self.bus = UnifiedEventBus()
        self.sse = SSEEventBus()
        self.poll = PollEventBus()
        self.bus.register(self.sse)
        self.bus.register(self.poll)

    def test_publish_to_all_adapters(self):
        """测试发布到所有 adapter"""
        sse_cb = MagicMock()
        poll_cb = MagicMock()
        self.sse.subscribe("test", sse_cb)
        self.poll.subscribe("test", poll_cb)

        event = make_event(event_type="test")
        self.bus.publish(event)

        sse_cb.assert_called_once()
        poll_cb.assert_called_once()

    def test_emit(self):
        """测试便捷发布"""
        self.bus.emit("step_started", "wf-1", step_id="s1", data={"key": "val"})

        poll_events = self.poll.get_events_after()
        assert len(poll_events) == 1
        assert poll_events[0]["event_type"] == "step_started"
        assert poll_events[0]["workflow_id"] == "wf-1"

    def test_register_unregister(self):
        """测试注册和注销 adapter"""
        assert len(self.bus._adapters) == 2

        self.bus.unregister(self.sse)
        assert len(self.bus._adapters) == 1
        assert self.bus.get_adapter(SSEEventBus) is None

    def test_get_adapter(self):
        """测试按类型获取 adapter"""
        sse = self.bus.get_adapter(SSEEventBus)
        poll = self.bus.get_adapter(PollEventBus)

        assert isinstance(sse, SSEEventBus)
        assert isinstance(poll, PollEventBus)

    def test_get_stats(self):
        """测试统计信息"""
        stats = self.bus.get_stats()
        assert stats["type"] == "unified"
        assert stats["adapter_count"] == 2
        assert len(stats["adapters"]) == 2

    def test_unified_subscribe(self):
        """测试统一订阅"""
        callback = MagicMock()
        unsubscribe = self.bus.subscribe("test", callback)

        self.bus.emit("test", "wf-1")

        callback.assert_called()
        unsubscribe()

    def test_unsubscribe_from_all(self):
        """测试取消订阅从所有 adapter"""
        callback = MagicMock()
        unsubscribe = self.bus.subscribe("test", callback)
        unsubscribe()

        self.bus.emit("test", "wf-1")
        # callback 应该只在 UnifiedEventBus 自身订阅中被移除
        # adapter 自身的订阅也被移除

    def test_publish_error_in_one_adapter(self):
        """测试单个 adapter 发布错误不影响其他"""
        broken_bus = MagicMock(spec=EventBus)
        broken_bus.publish.side_effect = RuntimeError("broken")
        broken_bus.subscribe.return_value = lambda: None
        broken_bus.subscribe_global.return_value = lambda: None

        self.bus.register(broken_bus)

        poll_cb = MagicMock()
        self.poll.subscribe("test", poll_cb)

        # 不应抛出异常
        self.bus.emit("test", "wf-1")

        # Poll adapter 应该仍然收到事件
        poll_events = self.poll.get_events_after()
        assert len(poll_events) >= 1


# ============================================================================
# make_tracker_callback 测试
# ============================================================================

class TestMakeTrackerCallback:
    """Tracker 回调兼容性测试"""

    def setup_method(self):
        self.bus = UnifiedEventBus()
        self.bus.register(PollEventBus())

    def test_tracker_callback_basic(self):
        """测试基本 tracker 回调"""
        callback = make_tracker_callback(self.bus)

        callback({
            "event_type": "step_started",
            "workflow_id": "wf-1",
            "step_id": "s1",
            "data": {"agent": "test"},
        })

        poll_adapter = self.bus.get_adapter(PollEventBus)
        events = poll_adapter.get_events_after()
        assert len(events) == 1
        assert events[0]["event_type"] == "step_started"

    def test_tracker_callback_event_mapping(self):
        """测试事件类型映射"""
        callback = make_tracker_callback(self.bus)

        # 测试各种映射
        mappings = [
            ("step_completed", "step_completed"),
            ("workflow_error", "workflow_failed"),
            ("step_cancelled", "step_failed"),
            ("workflow_paused", "workflow_paused"),
            ("steps_blocked", "steps_blocked"),
        ]

        for input_type, expected_type in mappings:
            callback({
                "event_type": input_type,
                "workflow_id": "wf-1",
            })

        poll_adapter = self.bus.get_adapter(PollEventBus)
        events = poll_adapter.get_events_after()
        event_types = [e["event_type"] for e in events]
        for _, expected in mappings:
            assert expected in event_types

    def test_tracker_callback_default_bus(self):
        """测试使用默认全局事件总线"""
        reset_event_bus()
        try:
            callback = make_tracker_callback()
            callback({
                "event_type": "test",
                "workflow_id": "wf-1",
            })
            # 不应抛出异常
        finally:
            reset_event_bus()


# ============================================================================
# 全局单例测试
# ============================================================================

class TestGlobalSingleton:
    """全局单例和辅助函数测试"""

    def teardown_method(self):
        reset_event_bus()

    def test_get_event_bus_returns_unified(self):
        """get_event_bus 返回 UnifiedEventBus"""
        bus = get_event_bus()
        assert isinstance(bus, UnifiedEventBus)

    def test_get_event_bus_singleton(self):
        """get_event_bus 返回同一个实例"""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2

    def test_default_adapters_registered(self):
        """默认注册了 SSE + Poll adapter"""
        bus = get_event_bus()
        assert bus.get_adapter(SSEEventBus) is not None
        assert bus.get_adapter(PollEventBus) is not None

    def test_get_sse_adapter(self):
        """获取 SSE adapter"""
        sse = get_sse_adapter()
        assert isinstance(sse, SSEEventBus)

    def test_get_poll_adapter(self):
        """获取 Poll adapter"""
        poll = get_poll_adapter()
        assert isinstance(poll, PollEventBus)

    def test_reset_event_bus(self):
        """重置事件总线"""
        bus1 = get_event_bus()
        reset_event_bus()
        bus2 = get_event_bus()
        assert bus1 is not bus2


# ============================================================================
# 向后兼容测试
# ============================================================================

class TestBackwardCompatibility:
    """向后兼容性测试"""

    def teardown_method(self):
        reset_event_bus()

    def test_old_imports_work(self):
        """测试旧的导入路径仍然可用"""
        from reins.common.events import (
            EventType,
            WorkflowEvent,
            get_event_bus,
            make_tracker_callback,
            router,
        )

        assert EventType is not None
        assert WorkflowEvent is not None
        assert callable(get_event_bus)
        assert callable(make_tracker_callback)
        assert router is not None

    def test_events_module_router_prefix(self):
        """测试 router 前缀正确"""
        from reins.common.events import router
        assert router.prefix == "/api/v1/events"

    def test_tracker_callback_integration(self):
        """测试 tracker callback 与完整流程集成"""
        reset_event_bus()
        bus = get_event_bus()

        callback = make_tracker_callback()

        # 模拟 WorkflowExecutionEngine 的事件
        callback({
            "event_type": "workflow_started",
            "workflow_id": "wf-123",
            "step_id": "",
            "data": {"total_steps": 5},
        })

        callback({
            "event_type": "step_started",
            "workflow_id": "wf-123",
            "step_id": "step-1",
            "data": {"name": "态势感知"},
        })

        callback({
            "event_type": "step_completed",
            "workflow_id": "wf-123",
            "step_id": "step-1",
            "data": {"result": "ok"},
        })

        # 验证 Poll adapter 收到所有事件
        poll = get_poll_adapter()
        events = poll.get_events_after()
        assert len(events) == 3
        assert events[0]["event_type"] == "workflow_started"
        assert events[1]["event_type"] == "step_started"
        assert events[2]["event_type"] == "step_completed"
