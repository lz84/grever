# -*- coding: utf-8 -*-
"""
State Machine & DAGScheduler Unit Tests

MAK-153: 单元测试 - 核心引擎（状态机、DAG调度、并行管理）

测试覆盖：
1. TaskState 状态转换（valid transitions）
2. TransitionError 无效转换异常
3. DAGScheduler 循环检测
4. DAGScheduler 拓扑排序
5. DAGScheduler 并行分组
6. DAGScheduler get_ready_tasks
"""

import pytest
import logging
import sys
import asyncio
from pathlib import Path

src_dir = str(Path(__file__).parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from reins.core.engine import (
    TaskState, TransitionError, StateTransition, Task,
    DAGScheduler,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# TaskState Transitions Tests
# ============================================================================

class TestTaskStateTransitions:
    """TaskState 状态转换测试"""

    def test_valid_transitions_from_created(self):
        """CREATED 状态的有效转换"""
        task = Task(id="task-1", title="Test Task")
        assert task.state == TaskState.CREATED

        # CREATED -> DECOMPOSED
        t = task.transition_to(TaskState.DECOMPOSED, "decompose")
        assert task.state == TaskState.DECOMPOSED
        assert t.from_state == TaskState.CREATED
        assert t.to_state == TaskState.DECOMPOSED

        # DECOMPOSED -> WAITING
        t2 = task.transition_to(TaskState.WAITING, "wait for deps")
        assert task.state == TaskState.WAITING

    def test_valid_transitions_from_decomposed(self):
        """DECOMPOSED 状态的有效转换"""
        task = Task(id="task-1", title="Test Task")
        task.transition_to(TaskState.DECOMPOSED)

        # DECOMPOSED -> RUNNING (skip waiting)
        t = task.transition_to(TaskState.RUNNING, "start now")
        assert task.state == TaskState.RUNNING

    def test_valid_transitions_from_waiting(self):
        """WAITING 状态的有效转换"""
        task = Task(id="task-1", title="Test Task")
        task.transition_to(TaskState.DECOMPOSED)
        task.transition_to(TaskState.WAITING)

        # WAITING -> RUNNING
        t = task.transition_to(TaskState.RUNNING, "start")
        assert task.state == TaskState.RUNNING

        # WAITING -> FAILED (blocked by failed dep)
        task2 = Task(id="task-2", title="Test Task 2")
        task2.transition_to(TaskState.DECOMPOSED)
        task2.transition_to(TaskState.WAITING)
        t2 = task2.transition_to(TaskState.FAILED, "blocked by failed dep")
        assert task2.state == TaskState.FAILED

    def test_valid_transitions_from_running(self):
        """RUNNING 状态的有效转换"""
        task = Task(id="task-1", title="Test Task")
        task.transition_to(TaskState.DECOMPOSED)
        task.transition_to(TaskState.RUNNING)
        assert task.started_at is not None

        # RUNNING -> COMPLETED
        t = task.transition_to(TaskState.COMPLETED, "done")
        assert task.state == TaskState.COMPLETED
        assert task.completed_at is not None

    def test_invalid_transition_raises_error(self):
        """无效状态转换抛出 TransitionError"""
        task = Task(id="task-1", title="Test Task")

        # CREATED -> COMPLETED (invalid - must go through DECOMPOSED/WAITING/RUNNING)
        with pytest.raises(TransitionError) as exc_info:
            task.transition_to(TaskState.COMPLETED)
        # Error message contains Chinese chars, check exception was raised
        assert exc_info.value is not None

    def test_invalid_transition_waiting_to_completed(self):
        """WAITING -> COMPLETED is invalid"""
        task = Task(id="task-1", title="Test Task")
        task.transition_to(TaskState.DECOMPOSED)
        task.transition_to(TaskState.WAITING)

        with pytest.raises(TransitionError):
            task.transition_to(TaskState.COMPLETED)

    def test_completed_is_final(self):
        """COMPLETED 是终态，不能再转换"""
        task = Task(id="task-1", title="Test Task")
        task.transition_to(TaskState.DECOMPOSED)
        task.transition_to(TaskState.RUNNING)
        task.transition_to(TaskState.COMPLETED)

        with pytest.raises(TransitionError):
            task.transition_to(TaskState.RUNNING)

    def test_cancelled_is_final(self):
        """CANCELLED 是终态"""
        task = Task(id="task-1", title="Test Task")
        task.transition_to(TaskState.CANCELLED, "user cancelled")

        with pytest.raises(TransitionError):
            task.transition_to(TaskState.RUNNING)

    def test_failed_can_retry(self):
        """FAILED 可以重试 -> DECOMPOSED"""
        task = Task(id="task-1", title="Test Task")
        task.transition_to(TaskState.DECOMPOSED)
        task.transition_to(TaskState.RUNNING)
        task.transition_to(TaskState.FAILED, "execution error")

        # FAILED -> DECOMPOSED (retry)
        t = task.transition_to(TaskState.DECOMPOSED, "retry")
        assert task.state == TaskState.DECOMPOSED

    def test_failed_can_cancel(self):
        """FAILED 可以取消"""
        task = Task(id="task-1", title="Test Task")
        task.transition_to(TaskState.DECOMPOSED)
        task.transition_to(TaskState.RUNNING)
        task.transition_to(TaskState.FAILED)
        task.transition_to(TaskState.CANCELLED, "give up")

        assert task.state == TaskState.CANCELLED

    def test_running_to_cancelled(self):
        """RUNNING -> CANCELLED"""
        task = Task(id="task-1", title="Test Task")
        task.transition_to(TaskState.DECOMPOSED)
        task.transition_to(TaskState.RUNNING)

        t = task.transition_to(TaskState.CANCELLED, "user cancel")
        assert task.state == TaskState.CANCELLED
        assert task.completed_at is not None

    def test_transition_records_timestamp(self):
        """状态转换记录时间戳"""
        task = Task(id="task-1", title="Test Task")
        t = task.transition_to(TaskState.DECOMPOSED, "decompose")
        assert t.timestamp is not None
        assert t.reason == "decompose"

    def test_state_to_dict(self):
        """Task.to_dict() 包含完整状态"""
        task = Task(id="task-1", title="Test Task")
        d = task.to_dict()
        assert d["id"] == "task-1"
        assert d["title"] == "Test Task"
        assert d["state"] == "created"
        assert "dependencies" in d
        assert "dependents" in d


# ============================================================================
# DAGScheduler Tests
# ============================================================================

class TestDAGScheduler:
    """DAGScheduler 调度器测试"""

    def test_add_task_single(self):
        """添加单个任务"""
        scheduler = DAGScheduler()
        scheduler.add_task("task-1")
        assert "task-1" in scheduler.graph

    def test_add_task_with_dependencies(self):
        """添加有依赖的任务"""
        scheduler = DAGScheduler()
        scheduler.add_task("task-2", dependencies=["task-1"])

        assert "task-1" in scheduler.graph
        assert "task-2" in scheduler.graph
        assert "task-1" in scheduler.graph["task-2"]
        assert "task-2" in scheduler.reverse_graph["task-1"]

    def test_detect_cycle_no_cycle(self):
        """无环图检测"""
        scheduler = DAGScheduler()
        scheduler.add_task("a")
        scheduler.add_task("b", dependencies=["a"])
        scheduler.add_task("c", dependencies=["b"])

        cycle = scheduler.detect_cycle()
        assert cycle is None

    def test_detect_cycle_with_cycle(self):
        """有环图检测"""
        scheduler = DAGScheduler()
        scheduler.add_task("a", dependencies=["c"])
        scheduler.add_task("b", dependencies=["a"])
        scheduler.add_task("c", dependencies=["b"])  # a -> b -> c -> a

        cycle = scheduler.detect_cycle()
        assert cycle is not None
        assert "a" in cycle

    def test_detect_cycle_self_loop(self):
        """自环检测"""
        scheduler = DAGScheduler()
        scheduler.add_task("a", dependencies=["a"])

        cycle = scheduler.detect_cycle()
        assert cycle is not None

    def test_topological_sort_linear(self):
        """线性拓扑排序"""
        scheduler = DAGScheduler()
        scheduler.add_task("a")
        scheduler.add_task("b", dependencies=["a"])
        scheduler.add_task("c", dependencies=["b"])

        order = scheduler.topological_sort()
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_topological_sort_parallel(self):
        """并行任务拓扑排序"""
        scheduler = DAGScheduler()
        scheduler.add_task("a")
        scheduler.add_task("b")
        scheduler.add_task("c", dependencies=["a", "b"])

        order = scheduler.topological_sort()
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("c")
        # a and b order not guaranteed

    def test_topological_sort_raises_on_cycle(self):
        """有环时拓扑排序抛出异常"""
        scheduler = DAGScheduler()
        scheduler.add_task("a", dependencies=["c"])
        scheduler.add_task("b", dependencies=["a"])
        scheduler.add_task("c", dependencies=["b"])

        with pytest.raises(ValueError) as exc_info:
            scheduler.topological_sort()
        # Exception raised with cycle info
        assert exc_info.value is not None

    def test_get_ready_tasks_initial(self):
        """初始状态获取就绪任务"""
        scheduler = DAGScheduler()
        scheduler.add_task("a")
        scheduler.add_task("b", dependencies=["a"])
        scheduler.add_task("c", dependencies=["b"])

        ready = scheduler.get_ready_tasks(set(), set())
        assert ready == ["a"]

    def test_get_ready_tasks_after_complete(self):
        """完成后获取就绪任务"""
        scheduler = DAGScheduler()
        scheduler.add_task("a")
        scheduler.add_task("b", dependencies=["a"])
        scheduler.add_task("c", dependencies=["b"])

        ready = scheduler.get_ready_tasks({"a"}, set())
        assert ready == ["b"]

    def test_get_ready_tasks_skips_failed_deps(self):
        """跳过有失败依赖的任务"""
        scheduler = DAGScheduler()
        scheduler.add_task("a")
        scheduler.add_task("b", dependencies=["a"])
        scheduler.add_task("c", dependencies=["b"])

        ready = scheduler.get_ready_tasks(set(), {"a"})
        assert "b" not in ready
        assert "c" not in ready

    def test_get_parallel_groups(self):
        """并行分组"""
        scheduler = DAGScheduler()
        scheduler.add_task("a")
        scheduler.add_task("b")
        scheduler.add_task("c", dependencies=["a", "b"])

        groups = scheduler.get_parallel_groups()
        assert len(groups) == 2
        assert set(groups[0]) == {"a", "b"}
        assert groups[1] == {"c"}

    def test_get_parallel_groups_complex(self):
        """复杂并行分组"""
        scheduler = DAGScheduler()
        # a, b 并行 -> c -> d, e 并行 -> f
        scheduler.add_task("a")
        scheduler.add_task("b")
        scheduler.add_task("c", dependencies=["a", "b"])
        scheduler.add_task("d", dependencies=["c"])
        scheduler.add_task("e", dependencies=["c"])
        scheduler.add_task("f", dependencies=["d", "e"])

        groups = scheduler.get_parallel_groups()
        assert len(groups) == 4
        assert set(groups[0]) == {"a", "b"}
        assert groups[1] == {"c"}
        assert set(groups[2]) == {"d", "e"}
        assert groups[3] == {"f"}

    def test_get_parallel_groups_raises_on_cycle(self):
        """有环时并行分组抛出异常"""
        scheduler = DAGScheduler()
        scheduler.add_task("a", dependencies=["b"])
        scheduler.add_task("b", dependencies=["a"])

        with pytest.raises(ValueError):
            scheduler.get_parallel_groups()

    def test_empty_graph(self):
        """空图"""
        scheduler = DAGScheduler()
        ready = scheduler.get_ready_tasks(set(), set())
        assert ready == []
        groups = scheduler.get_parallel_groups()
        assert groups == []


# ============================================================================
# Integration Tests
# ============================================================================

class TestStateMachineDAGIntegration:
    """状态机与DAG调度集成测试"""

    def test_task_completion_triggers_dependents(self):
        """任务完成后触发依赖任务"""
        scheduler = DAGScheduler()
        scheduler.add_task("a")
        scheduler.add_task("b", dependencies=["a"])

        # a 完成，b 应该就绪
        ready = scheduler.get_ready_tasks({"a"}, set())
        assert "b" in ready

    def test_failed_task_blocks_dependents(self):
        """失败任务阻止依赖任务"""
        scheduler = DAGScheduler()
        scheduler.add_task("a")
        scheduler.add_task("b", dependencies=["a"])

        # a 失败，b 不应该就绪
        ready = scheduler.get_ready_tasks(set(), {"a"})
        assert "b" not in ready

    def test_multiple_dependencies_all_must_complete(self):
        """多依赖全部完成才触发"""
        scheduler = DAGScheduler()
        scheduler.add_task("a")
        scheduler.add_task("b")
        scheduler.add_task("c", dependencies=["a", "b"])

        # 只有 a 完成，c 不就绪
        ready = scheduler.get_ready_tasks({"a"}, set())
        assert "c" not in ready

        # a, b 都完成，c 就绪
        ready = scheduler.get_ready_tasks({"a", "b"}, set())
        assert "c" in ready


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
