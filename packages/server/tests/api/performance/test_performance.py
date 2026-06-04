# -*- coding: utf-8 -*-
"""
Performance Tests

MAK-158: 性能测试 - 页面加载<3s, API<1s

测试覆盖：
1. DAG调度性能（1000+ 节点）
2. 状态转换性能
3. 并行调度性能基准
4. 内存使用基准
"""

import pytest
import asyncio
import logging
import sys
import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

src_dir = str(Path(__file__).parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from reins.core.engine import TaskState, Task, DAGScheduler
from reins.core.workflow_engine import WorkflowExecutionEngine, ExecutionState
from models import (
    SqlWorkflow, SqlWorkflowStep,
    WorkflowStatus, WorkflowStepStatus,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Performance Benchmarks
# ============================================================================

class TestDAGSchedulerPerformance:
    """DAG调度器性能测试"""

    def test_detect_cycle_performance_1000_nodes(self):
        """1000节点无环图循环检测性能 < 100ms"""
        scheduler = DAGScheduler()

        # 创建1000个节点线性链
        for i in range(1000):
            if i == 0:
                scheduler.add_task(f"node-{i}")
            else:
                scheduler.add_task(f"node-{i}", dependencies=[f"node-{i-1}"])

        start = time.perf_counter()
        cycle = scheduler.detect_cycle()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert cycle is None
        assert elapsed_ms < 100, f"Cycle detection took {elapsed_ms:.2f}ms, expected < 100ms"
        logger.info(f"? Cycle detection (1000 nodes): {elapsed_ms:.2f}ms < 100ms threshold")

    def test_topological_sort_performance_1000_nodes(self):
        """1000节点拓扑排序性能 < 200ms"""
        scheduler = DAGScheduler()

        # 创建1000个节点线性链
        for i in range(1000):
            if i == 0:
                scheduler.add_task(f"node-{i}")
            else:
                scheduler.add_task(f"node-{i}", dependencies=[f"node-{i-1}"])

        start = time.perf_counter()
        order = scheduler.topological_sort()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(order) == 1000
        assert elapsed_ms < 200, f"Topological sort took {elapsed_ms:.2f}ms, expected < 200ms"
        logger.info(f"? Topological sort (1000 nodes): {elapsed_ms:.2f}ms < 200ms threshold")

    def test_parallel_groups_performance_500_nodes(self):
        """500节点并行分组性能 < 150ms"""
        scheduler = DAGScheduler()

        # 创建500个并行组 (50组 x 10个并行)
        for group_idx in range(50):
            group_tasks = []
            for task_idx in range(10):
                task_id = f"g{group_idx}-t{task_idx}"
                deps = [] if group_idx == 0 else [f"g{group_idx-1}-t{j}" for j in range(10)]
                scheduler.add_task(task_id, dependencies=deps)

        start = time.perf_counter()
        groups = scheduler.get_parallel_groups()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(groups) == 50
        assert elapsed_ms < 150, f"Parallel groups took {elapsed_ms:.2f}ms, expected < 150ms"
        logger.info(f"? Parallel groups (500 nodes, 50 layers): {elapsed_ms:.2f}ms < 150ms threshold")

    def test_get_ready_tasks_performance_500_tasks(self):
        """500任务就绪查询性能 < 50ms"""
        scheduler = DAGScheduler()

        # 创建500个任务
        for i in range(500):
            if i == 0:
                scheduler.add_task(f"task-{i}")
            else:
                scheduler.add_task(f"task-{i}", dependencies=[f"task-{i-1}"])

        start = time.perf_counter()
        for _ in range(100):  # 重复100次
            ready = scheduler.get_ready_tasks(set(), set())
        elapsed_ms = (time.perf_counter() - start) * 1000

        # 100次查询应该在50ms内
        assert elapsed_ms < 50, f"100 ready-task queries took {elapsed_ms:.2f}ms, expected < 50ms"
        logger.info(f"? 100 ready-task queries (500 tasks): {elapsed_ms:.2f}ms < 50ms threshold")


class TestStateTransitionPerformance:
    """状态转换性能测试"""

    def test_rapid_state_transitions(self):
        """1000次状态转换性能 < 100ms"""
        tasks = [
            Task(id=f"perf-task-{i}", title=f"Perf Task {i}")
            for i in range(1000)
        ]

        start = time.perf_counter()
        for task in tasks:
            task.transition_to(TaskState.DECOMPOSED)
            task.transition_to(TaskState.RUNNING)
            task.transition_to(TaskState.COMPLETED)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"1000 state transitions took {elapsed_ms:.2f}ms, expected < 100ms"
        logger.info(f"? 1000 state transitions: {elapsed_ms:.2f}ms < 100ms threshold")

    def test_state_to_dict_performance(self):
        """1000次to_dict调用性能 < 100ms"""
        tasks = [
            Task(id=f"dict-task-{i}", title=f"Dict Task {i}")
            for i in range(1000)
        ]

        start = time.perf_counter()
        for task in tasks:
            task.to_dict()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"1000 to_dict calls took {elapsed_ms:.2f}ms, expected < 100ms"
        logger.info(f"? 1000 to_dict calls: {elapsed_ms:.2f}ms < 100ms threshold")


class TestWorkflowEnginePerformance:
    """Workflow引擎性能测试"""

    @pytest.mark.asyncio
    async def test_workflow_execution_performance_100_steps(self):
        """100步工作流执行性能 < 2s"""
        mock_db_manager = MagicMock()
        mock_db_manager.engine = MagicMock()

        workflow_id = str(uuid.uuid4())

        workflow = SqlWorkflow(
            id=workflow_id,
            status=WorkflowStatus.DRAFT,
            name="Perf Workflow",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # 创建100个串行步骤
        steps = []
        for i in range(100):
            step = SqlWorkflowStep(
                id=f"perf-step-{i}",
                workflow_id=workflow_id,
                name=f"Step {i}",
                status=WorkflowStepStatus.PENDING,
                dependencies=[f"perf-step-{i-1}"] if i > 0 else [],
                order=i,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            steps.append(step)

        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()

        mock_workflow_repo.get.return_value = workflow
        mock_step_repo.list_by_workflow.return_value = steps

        async def fast_executor(step):
            await asyncio.sleep(0.001)  # 1ms per step = 100ms total
            return {"status": "success"}

        with patch.object(WorkflowExecutionEngine, '_get_repositories',
                          return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(mock_db_manager, max_concurrency=10)
            engine.set_default_executor(fast_executor)

            start = time.perf_counter()
            result = await engine.execute(workflow_id)
            elapsed_s = time.perf_counter() - start

            assert result["success"] is True
            assert result["completed_steps"] == 100
            # 100 steps with 1ms each + overhead should be < 2s
            assert elapsed_s < 2.0, f"100-step workflow took {elapsed_s:.2f}s, expected < 2s"
            logger.info(f"? 100-step workflow execution: {elapsed_s:.2f}s < 2s threshold")

    @pytest.mark.asyncio
    async def test_parallel_workflow_50_groups(self):
        """50组并行任务执行性能 < 1s (每步0.5ms)"""
        mock_db_manager = MagicMock()
        mock_db_manager.engine = MagicMock()

        workflow_id = str(uuid.uuid4())

        workflow = SqlWorkflow(
            id=workflow_id,
            status=WorkflowStatus.DRAFT,
            name="Parallel Perf Workflow",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # 50组，每组10个并行步骤
        steps = []
        for group_idx in range(50):
            for task_idx in range(10):
                step_id = f"pperf-g{group_idx}-t{task_idx}"
                deps = [] if group_idx == 0 else [f"pperf-g{group_idx-1}-t{j}" for j in range(10)]
                step = SqlWorkflowStep(
                    id=step_id,
                    workflow_id=workflow_id,
                    name=f"Group {group_idx} Task {task_idx}",
                    status=WorkflowStepStatus.PENDING,
                    dependencies=deps,
                    order=group_idx * 10 + task_idx,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                steps.append(step)

        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()

        mock_workflow_repo.get.return_value = workflow
        mock_step_repo.list_by_workflow.return_value = steps

        async def fast_executor(step):
            await asyncio.sleep(0.0005)  # 0.5ms per step
            return {"status": "success"}

        with patch.object(WorkflowExecutionEngine, '_get_repositories',
                          return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(mock_db_manager, max_concurrency=50)
            engine.set_default_executor(fast_executor)

            start = time.perf_counter()
            result = await engine.execute(workflow_id)
            elapsed_s = time.perf_counter() - start

            assert result["success"] is True
            # 50 groups * 0.5ms (parallel within group) + overhead should be < 1s
            assert elapsed_s < 1.0, f"50-group parallel workflow took {elapsed_s:.2f}s, expected < 1s"
            logger.info(f"? 50-group parallel workflow (500 steps): {elapsed_s:.2f}s < 1s threshold")


class TestAPIResponseTime:
    """API响应时间测试（模拟）"""

    def test_dag_operations_under_api_load_simulation(self):
        """模拟API负载：100次DAG查询 < 500ms"""
        scheduler = DAGScheduler()

        # 100个节点
        for i in range(100):
            if i == 0:
                scheduler.add_task(f"api-task-{i}")
            else:
                scheduler.add_task(f"api-task-{i}", dependencies=[f"api-task-{i-1}"])

        start = time.perf_counter()
        for _ in range(100):
            scheduler.get_ready_tasks(set(), set())
            scheduler.topological_sort()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, f"100 DAG ops took {elapsed_ms:.2f}ms, expected < 500ms"
        logger.info(f"? 100 DAG operations (100 nodes): {elapsed_ms:.2f}ms < 500ms threshold (simulating API load)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
