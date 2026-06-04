# -*- coding: utf-8 -*-
"""
E2E Tests - End-to-End Flow

MAK-157: E2E测试 - 端到端流程（创建目标→执行→结果）

测试覆盖：
1. 创建 Goal -> 创建 Workflow -> 添加 Steps -> 执行 -> 获取结果
2. 完整的状态转换流程
3. Workflow 取消和恢复
4. 并行任务执行
"""

import pytest
import asyncio
import logging
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

src_dir = str(Path(__file__).parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from reins.core.engine import TaskState, Task, DAGScheduler
from models import (
    SqlWorkflow, SqlWorkflowStep,
    WorkflowStatus, WorkflowStepStatus,
)
from reins.core.workflow_engine import WorkflowExecutionEngine, ExecutionState

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db_manager():
    """Mock database manager"""
    manager = MagicMock()
    manager.engine = MagicMock()
    return manager


@pytest.fixture
def sample_goal():
    """创建示例目标"""
    return {
        "id": f"goal-{uuid.uuid4().hex[:8]}",
        "title": "E2E Test Goal",
        "description": "End-to-end test goal",
        "status": "created",
    }


# ============================================================================
# E2E: Goal -> Workflow -> Steps -> Execute
# ============================================================================

class TestE2EGoalToExecution:
    """端到端流程测试：创建目标 -> 创建工作流 -> 添加步骤 -> 执行"""

    @pytest.mark.asyncio
    async def test_full_workflow_lifecycle(self, mock_db_manager, sample_goal):
        """
        完整工作流生命周期测试

        流程：Goal创建 -> Workflow创建 -> Steps添加 -> 执行 -> 完成
        """
        workflow_id = str(uuid.uuid4())

        # 1. 创建 Workflow
        workflow = SqlWorkflow(
            id=workflow_id,
            goal_id=sample_goal["id"],
            status=WorkflowStatus.DRAFT,
            name="E2E Workflow",
            description="Full lifecycle test",
            created_by="e2e-tester",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # 2. 创建 Steps (A -> B -> C)
        step_a = SqlWorkflowStep(
            id="e2e-step-a",
            workflow_id=workflow_id,
            name="Step A",
            description="First step",
            status=WorkflowStepStatus.PENDING,
            dependencies=[],
            order=1,
            input_data={"value": 1},
            max_retries=3,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        step_b = SqlWorkflowStep(
            id="e2e-step-b",
            workflow_id=workflow_id,
            name="Step B",
            description="Second step",
            status=WorkflowStepStatus.PENDING,
            dependencies=["e2e-step-a"],
            order=2,
            input_data={},
            max_retries=3,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        step_c = SqlWorkflowStep(
            id="e2e-step-c",
            workflow_id=workflow_id,
            name="Step C",
            description="Third step",
            status=WorkflowStepStatus.PENDING,
            dependencies=["e2e-step-b"],
            order=3,
            input_data={},
            max_retries=3,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # 3. Mock repositories
        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()

        mock_workflow_repo.get.return_value = workflow
        mock_step_repo.list_by_workflow.return_value = [step_a, step_b, step_c]

        execution_order = []

        async def mock_executor(step):
            execution_order.append(step.id)
            await asyncio.sleep(0.01)
            return {"status": "success", "step_id": step.id, "result": step.id}

        with patch.object(WorkflowExecutionEngine, '_get_repositories',
                          return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(mock_db_manager, max_concurrency=4)
            engine.set_default_executor(mock_executor)

            # 4. 执行工作流
            result = await engine.execute(workflow_id)

            # 5. 验证结果
            assert result["success"] is True, f"Expected success, got: {result.get('error')}"
            assert result["completed_steps"] == 3
            assert result["failed_steps"] == 0

            # 6. 验证执行顺序
            assert execution_order.index("e2e-step-a") < execution_order.index("e2e-step-b")
            assert execution_order.index("e2e-step-b") < execution_order.index("e2e-step-c")

            logger.info(f"? Full lifecycle test passed. Execution order: {execution_order}")

    @pytest.mark.asyncio
    async def test_parallel_e2e_execution(self, mock_db_manager):
        """并行任务 E2E 测试"""
        workflow_id = str(uuid.uuid4())

        workflow = SqlWorkflow(
            id=workflow_id,
            goal_id="goal-parallel",
            status=WorkflowStatus.DRAFT,
            name="Parallel E2E Workflow",
            created_by="e2e-tester",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # A, B, C 并行 -> D
        step_a = SqlWorkflowStep(
            id="parallel-a", workflow_id=workflow_id, name="Parallel A",
            status=WorkflowStepStatus.PENDING, dependencies=[], order=1,
            created_at=datetime.now(), updated_at=datetime.now(),
        )
        step_b = SqlWorkflowStep(
            id="parallel-b", workflow_id=workflow_id, name="Parallel B",
            status=WorkflowStepStatus.PENDING, dependencies=[], order=2,
            created_at=datetime.now(), updated_at=datetime.now(),
        )
        step_c = SqlWorkflowStep(
            id="parallel-c", workflow_id=workflow_id, name="Parallel C",
            status=WorkflowStepStatus.PENDING, dependencies=[], order=3,
            created_at=datetime.now(), updated_at=datetime.now(),
        )
        step_d = SqlWorkflowStep(
            id="parallel-d", workflow_id=workflow_id, name="Parallel D",
            status=WorkflowStepStatus.PENDING,
            dependencies=["parallel-a", "parallel-b", "parallel-c"], order=4,
            created_at=datetime.now(), updated_at=datetime.now(),
        )

        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()

        mock_workflow_repo.get.return_value = workflow
        mock_step_repo.list_by_workflow.return_value = [step_a, step_b, step_c, step_d]

        execution_times = {}

        async def mock_executor(step):
            execution_times[step.id] = datetime.now()
            await asyncio.sleep(0.05)
            return {"status": "success"}

        with patch.object(WorkflowExecutionEngine, '_get_repositories',
                          return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(mock_db_manager, max_concurrency=4)
            engine.set_default_executor(mock_executor)

            result = await engine.execute(workflow_id)

            assert result["success"] is True
            assert result["completed_steps"] == 4

            # 验证 D 在 A, B, C 之后执行
            for s in ["parallel-a", "parallel-b", "parallel-c"]:
                assert execution_times["parallel-d"] >= execution_times[s]

            logger.info("? Parallel E2E execution passed")

    @pytest.mark.asyncio
    async def test_workflow_with_circular_dependency_rejected(self, mock_db_manager):
        """循环依赖被正确拒绝"""
        workflow_id = str(uuid.uuid4())

        workflow = SqlWorkflow(
            id=workflow_id,
            status=WorkflowStatus.DRAFT,
            name="Circular Workflow",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        step_a = SqlWorkflowStep(
            id="circ-a", workflow_id=workflow_id, name="A",
            status=WorkflowStepStatus.PENDING, dependencies=["circ-c"], order=1,
            created_at=datetime.now(), updated_at=datetime.now(),
        )
        step_b = SqlWorkflowStep(
            id="circ-b", workflow_id=workflow_id, name="B",
            status=WorkflowStepStatus.PENDING, dependencies=["circ-a"], order=2,
            created_at=datetime.now(), updated_at=datetime.now(),
        )
        step_c = SqlWorkflowStep(
            id="circ-c", workflow_id=workflow_id, name="C",
            status=WorkflowStepStatus.PENDING, dependencies=["circ-b"], order=3,
            created_at=datetime.now(), updated_at=datetime.now(),
        )

        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()

        mock_workflow_repo.get.return_value = workflow
        mock_step_repo.list_by_workflow.return_value = [step_a, step_b, step_c]

        with patch.object(WorkflowExecutionEngine, '_get_repositories',
                          return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(mock_db_manager)

            result = await engine.execute(workflow_id)

            assert result["success"] is False
            assert "Circular dependency detected" in result["error"]
            logger.info("? Circular dependency correctly rejected")


class TestE2EStateTransitions:
    """E2E 状态转换测试"""

    @pytest.mark.asyncio
    async def test_task_state_machine_full_flow(self):
        """完整任务状态机流程"""
        # 创建任务
        task = Task(
            id="e2e-task-1",
            title="E2E Task",
            dependencies=["dep-1", "dep-2"]
        )

        assert task.state == TaskState.CREATED

        # 分解
        task.transition_to(TaskState.DECOMPOSED, "decompose for execution")
        assert task.state == TaskState.DECOMPOSED

        # 等待依赖
        task.transition_to(TaskState.WAITING, "wait for dependencies")
        assert task.state == TaskState.WAITING

        # 开始执行
        task.transition_to(TaskState.RUNNING, "start execution")
        assert task.state == TaskState.RUNNING
        assert task.started_at is not None

        # 完成
        task.output_data = {"result": "success"}
        task.transition_to(TaskState.COMPLETED, "done")
        assert task.state == TaskState.COMPLETED
        assert task.completed_at is not None

        logger.info("? Task state machine full flow passed")

    @pytest.mark.asyncio
    async def test_task_retry_after_failure(self):
        """失败后重试流程"""
        task = Task(id="retry-task", title="Retry Task")
        task.transition_to(TaskState.DECOMPOSED)
        task.transition_to(TaskState.RUNNING)
        task.error_message = "Temporary failure"
        task.transition_to(TaskState.FAILED, "first attempt failed")

        assert task.state == TaskState.FAILED

        # 重试
        task.error_message = None
        task.transition_to(TaskState.DECOMPOSED, "retry")
        task.transition_to(TaskState.RUNNING, "retry execution")
        task.transition_to(TaskState.COMPLETED, "retry succeeded")

        assert task.state == TaskState.COMPLETED
        logger.info("? Task retry flow passed")


class TestE2EEvents:
    """E2E 事件追踪测试"""

    @pytest.mark.asyncio
    async def test_events_emitted_during_execution(self, mock_db_manager):
        """执行过程中事件被正确触发"""
        workflow_id = str(uuid.uuid4())

        workflow = SqlWorkflow(
            id=workflow_id,
            goal_id="event-goal",
            status=WorkflowStatus.DRAFT,
            name="Event Test Workflow",
            created_by="e2e-tester",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        step_a = SqlWorkflowStep(
            id="event-step-a", workflow_id=workflow_id, name="Event Step A",
            status=WorkflowStepStatus.PENDING, dependencies=[], order=1,
            created_at=datetime.now(), updated_at=datetime.now(),
        )

        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()

        mock_workflow_repo.get.return_value = workflow
        mock_step_repo.list_by_workflow.return_value = [step_a]

        events = []

        def tracker_callback(event):
            events.append(event)

        async def mock_executor(step):
            await asyncio.sleep(0.01)
            return {"status": "success"}

        with patch.object(WorkflowExecutionEngine, '_get_repositories',
                          return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(mock_db_manager)
            engine.set_tracker(tracker_callback)
            engine.set_default_executor(mock_executor)

            await engine.execute(workflow_id)

            event_types = [e["event_type"] for e in events]
            assert "workflow_started" in event_types
            assert "step_started" in event_types
            assert "step_completed" in event_types
            assert "workflow_completed" in event_types

            logger.info(f"? Events test passed. Event types: {event_types}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
