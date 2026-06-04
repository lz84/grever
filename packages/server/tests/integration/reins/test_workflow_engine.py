"""
测试 Workflow 执行引擎

MAK-137: Workflow执行引擎
"""

import asyncio
import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from models import (
    SqlWorkflow, SqlWorkflowStep,
    WorkflowStatus, WorkflowStepStatus,
)
from reins.core.workflow_engine import (
    WorkflowExecutionEngine, ExecutionState,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def db_manager():
    """创建模拟的数据库管理器"""
    manager = MagicMock()
    manager.engine = MagicMock()
    return manager


@pytest.fixture
def workflow_engine(db_manager):
    """创建工作流执行引擎"""
    return WorkflowExecutionEngine(db_manager, max_concurrency=4)


@pytest.fixture
def sample_workflow():
    """创建示例工作流"""
    workflow_id = str(uuid.uuid4())
    return SqlWorkflow(
        id=workflow_id,
        goal_id="goal-1",
        status=WorkflowStatus.DRAFT,
        name="Test Workflow",
        description="A test workflow",
        created_by="tester",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_steps():
    """创建示例步骤（线性依赖：A -> B -> C）"""
    workflow_id = str(uuid.uuid4())
    
    step_a = SqlWorkflowStep(
        id="step-a",
        workflow_id=workflow_id,
        name="Step A",
        description="First step",
        status=WorkflowStepStatus.PENDING,
        dependencies=[],
        order=1,
        input_data={},
        max_retries=3,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    
    step_b = SqlWorkflowStep(
        id="step-b",
        workflow_id=workflow_id,
        name="Step B",
        description="Second step",
        status=WorkflowStepStatus.PENDING,
        dependencies=["step-a"],
        order=2,
        input_data={},
        max_retries=3,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    
    step_c = SqlWorkflowStep(
        id="step-c",
        workflow_id=workflow_id,
        name="Step C",
        description="Third step",
        status=WorkflowStepStatus.PENDING,
        dependencies=["step-b"],
        order=3,
        input_data={},
        max_retries=3,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    
    return [step_a, step_b, step_c]


@pytest.fixture
def parallel_steps():
    """创建并行步骤（A, B, C 互相独立，然后 D 依赖 A, B, C）"""
    workflow_id = str(uuid.uuid4())
    
    step_a = SqlWorkflowStep(
        id="parallel-a",
        workflow_id=workflow_id,
        name="Parallel A",
        status=WorkflowStepStatus.PENDING,
        dependencies=[],
        order=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    
    step_b = SqlWorkflowStep(
        id="parallel-b",
        workflow_id=workflow_id,
        name="Parallel B",
        status=WorkflowStepStatus.PENDING,
        dependencies=[],
        order=2,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    
    step_c = SqlWorkflowStep(
        id="parallel-c",
        workflow_id=workflow_id,
        name="Parallel C",
        status=WorkflowStepStatus.PENDING,
        dependencies=[],
        order=3,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    
    step_d = SqlWorkflowStep(
        id="parallel-d",
        workflow_id=workflow_id,
        name="Parallel D (depends on A, B, C)",
        status=WorkflowStepStatus.PENDING,
        dependencies=["parallel-a", "parallel-b", "parallel-c"],
        order=4,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    
    return [step_a, step_b, step_c, step_d]


# ============================================================================
# DAG 测试
# ============================================================================

class TestDAGOperations:
    """DAG 操作测试"""
    
    def test_build_dag_linear(self, workflow_engine, sample_steps):
        """测试线性依赖 DAG 构建"""
        dag = workflow_engine._build_dag(sample_steps)
        
        assert dag["step-a"] == set()
        assert dag["step-b"] == {"step-a"}
        assert dag["step-c"] == {"step-b"}
    
    def test_build_dag_parallel(self, workflow_engine, parallel_steps):
        """测试并行依赖 DAG 构建"""
        dag = workflow_engine._build_dag(parallel_steps)
        
        assert dag["parallel-a"] == set()
        assert dag["parallel-b"] == set()
        assert dag["parallel-c"] == set()
        assert dag["parallel-d"] == {"parallel-a", "parallel-b", "parallel-c"}
    
    def test_detect_cycle_no_cycle(self, workflow_engine, sample_steps):
        """测试无循环依赖检测"""
        dag = workflow_engine._build_dag(sample_steps)
        cycle = workflow_engine._detect_cycle(dag)
        
        assert cycle is None
    
    def test_detect_cycle_with_cycle(self, workflow_engine):
        """测试有循环依赖检测"""
        dag = {
            "a": {"b"},
            "b": {"c"},
            "c": {"a"},  # 循环: a -> b -> c -> a
        }
        
        cycle = workflow_engine._detect_cycle(dag)
        
        assert cycle is not None
        assert "a" in cycle
    
    def test_get_parallel_groups_linear(self, workflow_engine, sample_steps):
        """测试线性依赖分组"""
        dag = workflow_engine._build_dag(sample_steps)
        groups = workflow_engine._get_parallel_groups(dag, sample_steps)
        
        assert len(groups) == 3
        assert groups[0] == [sample_steps[0]]  # step-a
        assert groups[1] == [sample_steps[1]]  # step-b
        assert groups[2] == [sample_steps[2]]  # step-c
    
    def test_get_parallel_groups_parallel(self, workflow_engine, parallel_steps):
        """测试并行依赖分组"""
        dag = workflow_engine._build_dag(parallel_steps)
        groups = workflow_engine._get_parallel_groups(dag, parallel_steps)
        
        assert len(groups) == 2
        # 第一组: A, B, C 并行
        assert len(groups[0]) == 3
        assert set(s.id for s in groups[0]) == {"parallel-a", "parallel-b", "parallel-c"}
        # 第二组: D
        assert len(groups[1]) == 1
        assert groups[1][0].id == "parallel-d"


# ============================================================================
# 执行状态测试
# ============================================================================

class TestExecutionState:
    """执行状态测试"""
    
    def test_initial_state(self, workflow_engine):
        """测试初始状态"""
        assert workflow_engine.get_execution_state() == ExecutionState.IDLE
    
    def test_set_tracker(self, workflow_engine):
        """测试 tracker 设置"""
        callback = MagicMock()
        workflow_engine.set_tracker(callback)
        
        assert workflow_engine._tracker_callback is callback
    
    def test_emit_event(self, workflow_engine):
        """测试事件发送"""
        callback = MagicMock()
        workflow_engine.set_tracker(callback)
        workflow_engine._current_workflow_id = "test-workflow"
        
        workflow_engine._emit_event("test_event", "step-1", {"key": "value"})
        
        callback.assert_called_once()
        event = callback.call_args[0][0]
        assert event["event_type"] == "test_event"
        assert event["step_id"] == "step-1"
        assert event["workflow_id"] == "test-workflow"
        assert event["data"]["key"] == "value"


# ============================================================================
# 步骤执行器测试
# ============================================================================

class TestStepExecutors:
    """步骤执行器测试"""
    
    def test_set_step_executor(self, workflow_engine):
        """测试设置步骤执行器"""
        executor = AsyncMock(return_value={"result": "ok"})
        workflow_engine.set_step_executor("step-1", executor)
        
        assert workflow_engine._step_executors["step-1"] is executor
    
    def test_set_default_executor(self, workflow_engine):
        """测试设置默认执行器"""
        executor = AsyncMock(return_value={"result": "ok"})
        workflow_engine.set_default_executor(executor)
        
        assert workflow_engine._default_executor is executor


# ============================================================================
# 集成测试
# ============================================================================

class TestWorkflowExecution:
    """工作流执行集成测试"""
    
    @pytest.mark.asyncio
    async def test_execute_workflow_success(self, db_manager, sample_workflow, sample_steps):
        """测试成功执行工作流"""
        # Mock 仓库
        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()
        
        mock_workflow_repo.get.return_value = sample_workflow
        mock_step_repo.list_by_workflow.return_value = sample_steps
        
        with patch.object(WorkflowExecutionEngine, '_get_repositories', return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(db_manager)
            
            # 设置默认执行器
            async def mock_executor(step):
                await asyncio.sleep(0.01)  # 模拟执行
                return {"status": "success", "step_id": step.id}
            
            engine.set_default_executor(mock_executor)
            
            # 执行
            result = await engine.execute(sample_workflow.id)
            
            assert result["success"] is True
            assert result["completed_steps"] == 3
            assert result["failed_steps"] == 0
    
    @pytest.mark.asyncio
    async def test_execute_workflow_not_found(self, db_manager):
        """测试工作流不存在"""
        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()
        
        mock_workflow_repo.get.return_value = None
        
        with patch.object(WorkflowExecutionEngine, '_get_repositories', return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(db_manager)
            
            result = await engine.execute("non-existent-id")
            assert result["success"] is False
            assert "Workflow not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_workflow_no_steps(self, db_manager, sample_workflow):
        """测试工作流无步骤"""
        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()
        
        mock_workflow_repo.get.return_value = sample_workflow
        mock_step_repo.list_by_workflow.return_value = []
        
        with patch.object(WorkflowExecutionEngine, '_get_repositories', return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(db_manager)
            
            result = await engine.execute(sample_workflow.id)
            assert result["success"] is False
            assert "No steps found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_with_circular_dependency(self, db_manager):
        """测试循环依赖检测"""
        workflow_id = str(uuid.uuid4())
        workflow = SqlWorkflow(
            id=workflow_id,
            status=WorkflowStatus.DRAFT,
            name="Circular Workflow",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        # 创建循环依赖的步骤
        step_a = SqlWorkflowStep(
            id="circ-a",
            workflow_id=workflow_id,
            name="Step A",
            status=WorkflowStepStatus.PENDING,
            dependencies=["circ-c"],  # 依赖 C
            order=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        step_b = SqlWorkflowStep(
            id="circ-b",
            workflow_id=workflow_id,
            name="Step B",
            status=WorkflowStepStatus.PENDING,
            dependencies=["circ-a"],
            order=2,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        step_c = SqlWorkflowStep(
            id="circ-c",
            workflow_id=workflow_id,
            name="Step C",
            status=WorkflowStepStatus.PENDING,
            dependencies=["circ-b"],  # 依赖 B -> 循环
            order=3,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()
        
        mock_workflow_repo.get.return_value = workflow
        mock_step_repo.list_by_workflow.return_value = [step_a, step_b, step_c]
        
        with patch.object(WorkflowExecutionEngine, '_get_repositories', return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(db_manager)
            
            result = await engine.execute(workflow_id)
            assert result["success"] is False
            assert "Circular dependency detected" in result["error"]
    
    @pytest.mark.asyncio
    async def test_pause_and_resume(self, db_manager, sample_workflow, sample_steps):
        """测试暂停和恢复"""
        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()
        
        mock_workflow_repo.get.return_value = sample_workflow
        mock_step_repo.list_by_workflow.return_value = sample_steps
        
        with patch.object(WorkflowExecutionEngine, '_get_repositories', return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(db_manager)
            
            # 未运行时不能暂停
            with pytest.raises(RuntimeError, match="Cannot pause"):
                await engine.pause()
            
            # 未暂停时不能恢复
            with pytest.raises(RuntimeError, match="Cannot resume"):
                await engine.resume()
    
    @pytest.mark.asyncio
    async def test_cancel(self, db_manager, sample_workflow, sample_steps):
        """测试取消"""
        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()
        
        mock_workflow_repo.get.return_value = sample_workflow
        mock_step_repo.list_by_workflow.return_value = sample_steps
        
        with patch.object(WorkflowExecutionEngine, '_get_repositories', return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(db_manager)
            
            # 未运行时不能取消
            with pytest.raises(RuntimeError, match="Cannot cancel"):
                await engine.cancel()


class TestAddStep:
    """动态添加步骤测试"""
    
    @pytest.mark.asyncio
    async def test_add_step_success(self, db_manager):
        """测试成功添加步骤"""
        workflow_id = str(uuid.uuid4())
        
        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()
        
        mock_step_repo.list_by_workflow.return_value = [
            SqlWorkflowStep(
                id="existing-step",
                workflow_id=workflow_id,
                name="Existing",
                status=WorkflowStepStatus.DONE,
                order=1,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        ]
        
        with patch.object(WorkflowExecutionEngine, '_get_repositories', return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(db_manager)
            
            new_step = await engine.add_step(
                workflow_id,
                {"name": "New Step", "description": "Added dynamically"},
                dependencies=["existing-step"]
            )
            
            assert new_step.name == "New Step"
            assert new_step.dependencies == ["existing-step"]
            assert new_step.order == 2
            mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_add_step_while_running(self, db_manager):
        """测试运行时添加步骤（MAK-139: 应该成功，锁保护并发）"""
        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()
        
        mock_step_repo.list_by_workflow.return_value = []
        
        with patch.object(WorkflowExecutionEngine, '_get_repositories', return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(db_manager)
            engine._execution_state = ExecutionState.RUNNING
            
            # MAK-139: 运行时可以添加步骤（锁保护）
            # 注意：这里只是设置state但没有真正持有锁，所以add_step会成功
            new_step = await engine.add_step("workflow-1", {"name": "New Step"})
            assert new_step is not None
            assert new_step.name == "New Step"


# ============================================================================
# 并行执行测试
# ============================================================================

class TestParallelExecution:
    """并行执行测试"""
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, db_manager, parallel_steps):
        """测试并行执行"""
        workflow_id = parallel_steps[0].workflow_id
        
        workflow = SqlWorkflow(
            id=workflow_id,
            status=WorkflowStatus.DRAFT,
            name="Parallel Workflow",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()
        
        mock_workflow_repo.get.return_value = workflow
        mock_step_repo.list_by_workflow.return_value = parallel_steps
        
        execution_order = []
        
        async def mock_executor(step):
            execution_order.append(step.id)
            await asyncio.sleep(0.05)
            return {"result": "ok"}
        
        with patch.object(WorkflowExecutionEngine, '_get_repositories', return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(db_manager, max_concurrency=4)
            engine.set_default_executor(mock_executor)
            
            result = await engine.execute(workflow_id)
            
            assert result["success"] is True
            # 验证 A, B, C 在 D 之前执行
            for step_id in ["parallel-a", "parallel-b", "parallel-c"]:
                idx = execution_order.index(step_id)
                d_idx = execution_order.index("parallel-d")
                assert idx < d_idx


# ============================================================================
# 事件追踪测试
# ============================================================================

class TestEventTracking:
    """事件追踪测试"""
    
    @pytest.mark.asyncio
    async def test_events_emitted(self, db_manager, sample_workflow, sample_steps):
        """测试事件正确发送"""
        mock_session = MagicMock()
        mock_workflow_repo = MagicMock()
        mock_step_repo = MagicMock()
        
        mock_workflow_repo.get.return_value = sample_workflow
        mock_step_repo.list_by_workflow.return_value = sample_steps
        
        events = []
        
        def tracker_callback(event):
            events.append(event)
        
        async def mock_executor(step):
            await asyncio.sleep(0.01)
            return {"result": "ok"}
        
        with patch.object(WorkflowExecutionEngine, '_get_repositories', return_value=(mock_session, mock_workflow_repo, mock_step_repo)):
            engine = WorkflowExecutionEngine(db_manager)
            engine.set_tracker(tracker_callback)
            engine.set_default_executor(mock_executor)
            
            await engine.execute(sample_workflow.id)
            
            # 验证事件
            event_types = [e["event_type"] for e in events]
            assert "workflow_started" in event_types
            assert "step_started" in event_types
            assert "step_completed" in event_types
            assert "workflow_completed" in event_types


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
