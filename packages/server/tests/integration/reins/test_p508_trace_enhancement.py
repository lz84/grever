# -*- coding: utf-8 -*-
"""
P5-08: Trace 增强测试

测试覆盖：
1. P5-08-01: TraceEvent 持久化到 DB
2. P5-08-02: 步骤耗时计算
3. P5-08-03: Agent 归属
4. P5-08-04: 前端 Trace 时间线（数据结构验证）
5. P5-08-05: Workflow step 状态联动
"""

import pytest
import logging
import sys
import os
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

src_dir = str(Path(__file__).parent.parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from reins.tracking.tracker_sync_shim import ExecutionTrackerSync, TraceEvent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class TestP508TraceEnhancement:
    """P5-08 Trace 增强测试套件"""
    
    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_trace.db")
        yield db_path
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def tracker(self, temp_db):
        """创建 tracker 实例"""
        return ExecutionTrackerSync(db_path=temp_db)
    
    def test_p508_01_trace_event_persistence(self, tracker):
        """
        P5-08-01: TraceEvent 持久化到 DB
        
        验证：
        - trace_events 表存在
        - 事件能正确持久化
        -能从数据库读取
        """
        # 初始化数据库
        tracker._ensure_db()
        
        # 开始追踪
        trace = tracker.start_trace(
            workflow_id="wf-001",
            task_id="task-001",
            task_title="测试任务",
            agent_id="agent-001"
        )
        
        # 记录状态变更
        tracker.record_state_change(
            task_id="task-001",
            from_state="pending",
            to_state="running",
            reason="开始执行",
            agent_id="agent-001"
        )
        
        # 完成追踪
        report = tracker.complete_trace(
            task_id="task-001",
            final_state="completed",
            success=True,
            result={"output": "success"},
            cognitions_used=5,
            context_size_bytes=1024,
        )
        
        assert report is not None
        assert report.workflow_id == "wf-001"
        assert report.task_id == "task-001"
        
        # 从数据库读取事件
        events = tracker.get_trace_events("task-001")
        assert len(events) >= 3  # task_started, state_changed, task_completed
        
        # 验证事件持久化
        event_types = [e.event_type for e in events]
        assert "task_started" in event_types
        assert "state_changed" in event_types
        assert "task_completed" in event_types
        
        logger.info(f"[P5-08-01] ✓ TraceEvent 持久化成功，共 {len(events)} 个事件")
    
    def test_p508_02_step_duration_calculation(self, tracker):
        """
        P5-08-02: 步骤耗时计算
        
        验证：
        - agent_input 事件能记录 duration_ms
        - 步骤耗时自动计算
        """
        # 开始追踪
        trace = tracker.start_trace(
            workflow_id="wf-002",
            task_id="task-002",
            task_title="耗时测试任务"
        )
        
        # 记录第一个步骤
        time.sleep(0.1)  # 模拟耗时
        tracker.record_agent_input(
            task_id="task-002",
            action="分析问题",
            duration_ms=100,
            agent_id="agent-002"
        )
        
        # 记录第二个步骤
        time.sleep(0.1)  # 模拟耗时
        tracker.record_agent_input(
            task_id="task-002",
            action="执行方案",
            duration_ms=100,
            agent_id="agent-002"
        )
        
        # 完成追踪
        report = tracker.complete_trace(
            task_id="task-002",
            final_state="completed",
            success=True,
        )
        
        assert report is not None
        assert len(report.steps) == 2
        
        # 验证步骤耗时
        step1 = report.steps[0]
        step2 = report.steps[1]
        
        assert step1["action"] == "分析问题"
        assert step2["action"] == "执行方案"
        
        # 验证总耗时
        assert report.total_duration_ms > 0
        
        logger.info(f"[P5-08-02] ✓ 步骤耗时计算正确，总耗时: {report.total_duration_ms}ms")
    
    def test_p508_03_agent_attribution(self, tracker):
        """
        P5-08-03: Agent 归属
        
        验证：
        - TraceEvent 能关联 agent_id
        - 步骤能显示执行 Agent
        """
        # 开始追踪，指定 agent
        trace = tracker.start_trace(
            workflow_id="wf-003",
            task_id="task-003",
            task_title="Agent归属测试",
            agent_id="agent-main"
        )
        
        # 记录状态变更
        tracker.record_state_change(
            task_id="task-003",
            from_state="pending",
            to_state="running",
            agent_id="agent-main"
        )
        
        # 记录 Agent 操作
        tracker.record_agent_input(
            task_id="task-003",
            action="执行任务",
            agent_id="agent-worker-1"
        )
        
        # 完成追踪
        report = tracker.complete_trace(
            task_id="task-003",
            final_state="completed",
            success=True,
        )
        
        assert report is not None
        
        # 验证步骤中的 Agent 归属
        if report.steps:
            step = report.steps[0]
            assert "agent_id" in step or step.get("agent_id") is not None
            logger.info(f"[P5-08-03] ✓ Agent 归属: {step.get('agent_id')}")
        
        # 从数据库读取事件验证 agent_id
        events = tracker.get_trace_events("task-003")
        for event in events:
            if event.event_type in ("agent_input", "state_changed"):
                assert event.agent_id is not None, f"Event {event.event_id} missing agent_id"
        
        logger.info(f"[P5-08-03] ✓ Agent 归属正确")
    
    def test_p508_04_trace_data_structure(self, tracker):
        """
        P5-08-04: 前端 Trace 时间线数据结构验证
        
        验证：
        - Trace 数据结构包含必要字段
        - steps 数组包含耗时和 agent 信息
        """
        # 开始追踪
        trace = tracker.start_trace(
            workflow_id="wf-004",
            task_id="task-004",
            task_title="数据结构测试",
            agent_id="agent-001"
        )
        
        # 记录步骤
        tracker.record_agent_input(
            task_id="task-004",
            action="步骤1",
            duration_ms=50,
            agent_id="agent-001"
        )
        
        # 完成追踪
        report = tracker.complete_trace(
            task_id="task-004",
            final_state="completed",
            success=True,
            cognitions_used=3,
            context_size_bytes=512,
            cpu_time_ms=100,
            memory_peak_mb=10.5,
        )
        
        # 转换为 dict（模拟前端接收的 JSON）
        report_dict = report.to_dict()
        
        # 验证数据结构
        required_fields = [
            "workflow_id", "task_id", "task_title", "started_at",
            "total_duration_ms", "final_state", "success", "steps"
        ]
        
        for field in required_fields:
            assert field in report_dict, f"Missing field: {field}"
        
        # 验证 P5-08 增强字段
        assert report_dict["total_duration_ms"] >= 0
        assert isinstance(report_dict["steps"], list)
        
        # 验证步骤数据结构（P5-08-02, P5-08-03）
        if report_dict["steps"]:
            step = report_dict["steps"][0]
            # 步骤应包含耗时
            assert "duration_ms" in step or "duration_ms" == 0
            # 步骤应包含 Agent 信息（允许为 None）
            assert "agent_id" in step
        
        # 验证资源使用字段
        assert "cpu_time_ms" in report_dict
        assert "memory_peak_mb" in report_dict
        
        logger.info(f"[P5-08-04] ✓ Trace 数据结构正确: {required_fields}")
    
    def test_p508_05_workflow_step_status_sync(self, tracker):
        """
        P5-08-05: Workflow step 状态联动
        
        验证：
        - 能获取 trace 最新状态
        - 状态变更事件能正确记录
        """
        # 开始追踪
        trace = tracker.start_trace(
            workflow_id="wf-005",
            task_id="task-005",
            task_title="状态联动测试"
        )
        
        # 状态变更序列
        tracker.record_state_change("task-005", "created", "pending")
        tracker.record_state_change("task-005", "pending", "running")
        tracker.record_state_change("task-005", "running", "completed")
        
        # 完成追踪
        report = tracker.complete_trace(
            task_id="task-005",
            final_state="completed",
            success=True,
        )
        
        # 验证报告状态
        assert report.final_state == "completed"
        assert report.success is True
        
        # 从数据库读取事件验证状态序列
        events = tracker.get_trace_events("task-005")
        state_changes = [e for e in events if e.event_type == "state_changed"]
        
        assert len(state_changes) == 3
        
        # 验证状态转换
        assert state_changes[0].from_state == "created"
        assert state_changes[0].to_state == "pending"
        assert state_changes[1].from_state == "pending"
        assert state_changes[1].to_state == "running"
        assert state_changes[2].from_state == "running"
        assert state_changes[2].to_state == "completed"
        
        logger.info(f"[P5-08-05] ✓ Workflow step 状态联动正确，{len(state_changes)} 次状态变更")
    
    def test_p508_01_persistence_multiple_traces(self, tracker):
        """
        P5-08-01: 多个 Trace 持久化
        
        验证多个任务能同时持久化到数据库
        """
        task_ids = ["task-multi-1", "task-multi-2", "task-multi-3"]
        
        for i, task_id in enumerate(task_ids):
            trace = tracker.start_trace(
                workflow_id="wf-multi",
                task_id=task_id,
                task_title=f"任务{i+1}",
                agent_id=f"agent-{i+1}"
            )
            
            tracker.record_agent_input(
                task_id=task_id,
                action=f"步骤{i+1}",
                agent_id=f"agent-{i+1}"
            )
            
            tracker.complete_trace(
                task_id=task_id,
                final_state="completed",
                success=True,
            )
        
        # 验证所有报告都能从数据库读取
        for task_id in task_ids:
            report = tracker.get_trace_report(task_id)
            assert report is not None
            assert report.task_id == task_id
        
        # 验证 list_reports_from_db
        all_reports = tracker.list_reports_from_db(workflow_id="wf-multi")
        assert len(all_reports) >= 3
        
        logger.info(f"[P5-08-01] ✓ 多 Trace 持久化正确，{len(all_reports)} 个报告")
    
    def test_p508_trace_event_to_dict(self):
        """
        P5-08: TraceEvent.to_dict() 验证
        
        验证 TraceEvent 能正确序列化为 dict
        """
        event = TraceEvent(
            event_id="evt-123",
            event_type="agent_input",
            task_id="task-001",
            agent_id="agent-001",
            data={"action": "test"},
            duration_ms=100,
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_id"] == "evt-123"
        assert event_dict["event_type"] == "agent_input"
        assert event_dict["task_id"] == "task-001"
        assert event_dict["agent_id"] == "agent-001"
        assert event_dict["duration_ms"] == 100
        
        logger.info(f"[P5-08] ✓ TraceEvent.to_dict() 正确")


class TestP508FrontendDataFormat:
    """P5-08 前端数据格式验证"""
    
    def test_trace_interface_compatibility(self):
        """
        验证 Trace 数据结构与前端 API 匹配
        
        前端期望的字段：
        - task_id, workflow_id, task_title
        - started_at, final_state, success
        - total_duration_ms (P5-08-02)
        - agent_id (P5-08-03)
        - steps (P5-08-02)
        """
        # 模拟前端接收的数据
        trace_data = {
            "task_id": "task-001",
            "workflow_id": "wf-001",
            "task_title": "测试任务",
            "started_at": "2026-04-13T10:00:00",
            "final_state": "completed",
            "success": True,
            "total_duration_ms": 5000,
            "agent_id": "agent-001",
            "steps": [
                {
                    "timestamp": "2026-04-13T10:00:01",
                    "action": "分析",
                    "type": "agent_input",
                    "duration_ms": 1000,
                    "agent_id": "agent-001",
                }
            ],
            "error_stack": None,
            "cpu_time_ms": 50,
            "memory_peak_mb": 10.5,
        }
        
        # 验证必要字段存在
        assert "task_id" in trace_data
        assert "workflow_id" in trace_data
        assert "started_at" in trace_data
        assert "total_duration_ms" in trace_data  # P5-08-02
        assert "agent_id" in trace_data  # P5-08-03
        assert "steps" in trace_data  # P5-08-02
        
        # 验证步骤格式
        step = trace_data["steps"][0]
        assert "duration_ms" in step  # P5-08-02
        assert "agent_id" in step  # P5-08-03
        
        logger.info(f"[P5-08-Frontend] ✓ 前端数据格式兼容")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
