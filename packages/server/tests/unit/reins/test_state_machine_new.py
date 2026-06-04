# -*- coding: utf-8 -*-
"""
单元测试: reins/state_machine.py (基于 transitions 的新状态机)

覆盖:
1. TaskStateMachine - 状态转换
2. TaskStateSideEffects - 状态副作用
3. TaskActivityLog - 活动日志
4. InvalidStateTransitionError - 异常
5. TaskStateTransition - 向后兼容层
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

src_dir = str(Path(__file__).parent.parent.parent / 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from reins.core.state_machine import (
    TaskStateMachine,
    TaskStateSideEffects,
    TaskActivityLog,
    InvalidStateTransitionError,
    TaskStateTransition,
)
from models.enums import TaskState


# ============================================================================
# TaskStateMachine Tests
# ============================================================================

class TestTaskStateMachine:
    """TaskStateMachine 状态机测试"""

    def _make_task(self, task_id='task-1', status='backlog'):
        return {'id': task_id, 'status': status}

    def test_initial_state(self):
        """测试初始状态为 backlog"""
        sm = TaskStateMachine()
        assert sm.state == 'backlog'

    def test_valid_transition_backlog_to_todo(self):
        """测试 backlog → todo"""
        sm = TaskStateMachine()
        task = self._make_task()
        result = sm.transition(task, TaskState.TODO)
        assert result['status'] == 'todo'
        assert sm.state == 'todo'

    def test_valid_transition_todo_to_in_progress(self):
        """测试 todo → in_progress"""
        sm = TaskStateMachine()
        task = self._make_task(status='todo')
        sm.state = 'todo'
        result = sm.transition(task, TaskState.IN_PROGRESS)
        assert result['status'] == 'in_progress'
        assert sm.state == 'in_progress'

    def test_valid_transition_in_progress_to_in_review(self):
        """测试 in_progress → in_review"""
        sm = TaskStateMachine()
        task = self._make_task(status='in_progress')
        sm.state = 'in_progress'
        result = sm.transition(task, TaskState.IN_REVIEW)
        assert result['status'] == 'in_review'

    def test_valid_transition_in_review_to_done(self):
        """测试 in_review → done"""
        sm = TaskStateMachine()
        task = self._make_task(status='in_review')
        sm.state = 'in_review'
        result = sm.transition(task, TaskState.DONE)
        assert result['status'] == 'done'

    def test_valid_transition_to_cancelled(self):
        """测试多种状态可以转换到 cancelled"""
        sm = TaskStateMachine()
        for state in ['backlog', 'todo', 'in_progress', 'in_review', 'blocked', 'done']:
            task = self._make_task(status=state)
            sm.state = state
            result = sm.transition(task, TaskState.CANCELLED)
            assert result['status'] == 'cancelled'
            sm = TaskStateMachine()  # 重置

    def test_valid_transition_blocked_to_todo(self):
        """测试 blocked → todo"""
        sm = TaskStateMachine()
        task = self._make_task(status='blocked')
        sm.state = 'blocked'
        result = sm.transition(task, TaskState.TODO)
        assert result['status'] == 'todo'

    def test_valid_transition_in_review_to_in_progress(self):
        """测试 in_review → in_progress (rework)"""
        sm = TaskStateMachine()
        task = self._make_task(status='in_review')
        sm.state = 'in_review'
        result = sm.transition(task, TaskState.IN_PROGRESS)
        assert result['status'] == 'in_progress'

    def test_invalid_transition(self):
        """测试非法状态转换抛出异常"""
        sm = TaskStateMachine()
        task = self._make_task(status='backlog')
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            sm.transition(task, TaskState.DONE)
        assert 'backlog' in str(exc_info.value)
        assert 'done' in str(exc_info.value)

    def test_idempotent_transition(self):
        """测试相同状态转换是幂等的"""
        sm = TaskStateMachine()
        task = self._make_task(status='todo')
        sm.state = 'todo'
        result = sm.transition(task, TaskState.TODO)
        assert result['status'] == 'todo'
        # 不应产生 activity log
        task_logs = sm.get_activity_logs(task_id='task-1')
        assert len(task_logs) == 0

    def test_transition_with_reason_and_actor(self):
        """测试带原因和操作者的转换"""
        sm = TaskStateMachine()
        task = self._make_task(status='todo')
        sm.state = 'todo'
        result = sm.transition(
            task,
            TaskState.BLOCKED,
            reason='Waiting for API key',
            actor='scheduler',
        )
        assert result['status'] == 'blocked'
        assert result.get('blocked_reason') == 'Waiting for API key'

        logs = sm.get_activity_logs(task_id='task-1')
        assert len(logs) == 1
        assert logs[0].reason == 'Waiting for API key'
        assert logs[0].actor == 'scheduler'

    def test_full_lifecycle(self):
        """测试完整生命周期"""
        sm = TaskStateMachine()
        task = self._make_task()

        # backlog → todo → in_progress → in_review → done
        for target in [TaskState.TODO, TaskState.IN_PROGRESS, TaskState.IN_REVIEW, TaskState.DONE]:
            sm.state = task.get('status', 'backlog')
            task = sm.transition(task, target)

        assert task['status'] == 'done'

    def test_activity_logs(self):
        """测试活动日志记录"""
        sm = TaskStateMachine()
        task = self._make_task()
        sm.state = 'backlog'
        sm.transition(task, TaskState.TODO)
        sm.state = 'todo'
        sm.transition(task, TaskState.IN_PROGRESS)

        all_logs = sm.get_activity_logs()
        assert len(all_logs) == 2
        assert all_logs[0].new_status == 'todo'
        assert all_logs[1].new_status == 'in_progress'

        # 按 task_id 过滤
        task_logs = sm.get_activity_logs(task_id='task-1')
        assert len(task_logs) == 2

        other_logs = sm.get_activity_logs(task_id='other')
        assert len(other_logs) == 0

    def test_log_listener(self):
        """测试 activity log 监听器"""
        sm = TaskStateMachine()
        received = []

        def listener(log):
            received.append(log)

        sm.add_log_listener(listener)
        task = self._make_task()
        sm.state = 'backlog'
        sm.transition(task, TaskState.TODO)

        assert len(received) == 1
        assert received[0].new_status == 'todo'

    def test_listener_error_does_not_break_transition(self):
        """测试监听器异常不影响状态转换"""
        sm = TaskStateMachine()

        def failing_listener(log):
            raise RuntimeError('listener error')

        sm.add_log_listener(failing_listener)
        task = self._make_task()
        sm.state = 'backlog'
        # 不应抛出异常
        result = sm.transition(task, TaskState.TODO)
        assert result['status'] == 'todo'


# ============================================================================
# TaskStateSideEffects Tests
# ============================================================================

class TestTaskStateSideEffects:
    """状态副作用测试"""

    def test_started_at_on_in_progress(self):
        """测试进入 in_progress 时设置 started_at"""
        task = {'id': 't1', 'status': 'todo'}
        result = TaskStateSideEffects.apply_side_effects(
            task, TaskState.TODO, TaskState.IN_PROGRESS
        )
        assert 'started_at' in result
        assert result['started_at'] is not None

    def test_completed_at_on_done(self):
        """测试进入 done 时设置 completed_at"""
        task = {'id': 't1', 'status': 'in_review'}
        result = TaskStateSideEffects.apply_side_effects(
            task, TaskState.IN_REVIEW, TaskState.DONE
        )
        assert 'completed_at' in result

    def test_cancelled_at_on_cancelled(self):
        """测试进入 cancelled 时设置 cancelled_at"""
        task = {'id': 't1', 'status': 'todo'}
        result = TaskStateSideEffects.apply_side_effects(
            task, TaskState.TODO, TaskState.CANCELLED
        )
        assert 'cancelled_at' in result

    def test_blocked_reason(self):
        """测试进入 blocked 时设置 blocked_reason"""
        task = {'id': 't1', 'status': 'todo'}
        result = TaskStateSideEffects.apply_side_effects(
            task, TaskState.TODO, TaskState.BLOCKED, reason='waiting for deps'
        )
        assert result['blocked_reason'] == 'waiting for deps'

    def test_clear_blocked_reason(self):
        """测试离开 blocked 时清除 blocked_reason"""
        task = {'id': 't1', 'status': 'blocked', 'blocked_reason': 'old reason'}
        result = TaskStateSideEffects.apply_side_effects(
            task, TaskState.BLOCKED, TaskState.TODO
        )
        assert result.get('blocked_reason') is None

    def test_timeout_reason(self):
        """测试进入 timeout 时设置 timeout_reason"""
        task = {'id': 't1', 'status': 'in_progress'}
        result = TaskStateSideEffects.apply_side_effects(
            task, TaskState.IN_PROGRESS, TaskState.TIMEOUT, reason='exceeded 30min'
        )
        assert result['timeout_reason'] == 'exceeded 30min'

    def test_updated_always_set(self):
        """测试 updated_at 始终被设置"""
        task = {'id': 't1', 'status': 'todo'}
        result = TaskStateSideEffects.apply_side_effects(
            task, TaskState.TODO, TaskState.IN_PROGRESS
        )
        assert 'updated_at' in result


# ============================================================================
# TaskActivityLog Tests
# ============================================================================

class TestTaskActivityLog:
    """活动日志测试"""

    def test_create(self):
        log = TaskActivityLog(
            id='log-1',
            task_id='task-1',
            old_status='todo',
            new_status='in_progress',
            reason='test',
            actor='scheduler',
        )
        assert log.id == 'log-1'
        assert log.task_id == 'task-1'
        assert log.old_status == 'todo'
        assert log.new_status == 'in_progress'

    def test_to_dict(self):
        log = TaskActivityLog(
            id='log-2',
            task_id='task-2',
            old_status='todo',
            new_status='done',
            timestamp=datetime.now(),
            extra={'key': 'value'},
        )
        d = log.to_dict()
        assert d['id'] == 'log-2'
        assert d['extra'] == {'key': 'value'}
        assert d['timestamp'] is not None


# ============================================================================
# InvalidStateTransitionError Tests
# ============================================================================

class TestInvalidStateTransitionError:
    """非法状态转换异常测试"""

    def test_error_message(self):
        err = InvalidStateTransitionError(
            from_state='backlog',
            to_state='done',
            allowed='todo, cancelled',
            task_id='task-1',
        )
        msg = str(err)
        assert 'backlog' in msg
        assert 'done' in msg
        assert 'task-1' in msg

    def test_to_dict(self):
        err = InvalidStateTransitionError(
            from_state='todo',
            to_state='done',
            allowed='in_progress, blocked, cancelled',
            task_id='task-2',
        )
        d = err.to_dict()
        assert d['error'] == 'invalid_state_transition'
        assert d['from_state'] == 'todo'
        assert d['to_state'] == 'done'
        assert d['task_id'] == 'task-2'
        assert 'in_progress' in d['allowed_transitions']

    def test_error_without_allowed(self):
        err = InvalidStateTransitionError(
            from_state='todo',
            to_state='done',
        )
        msg = str(err)
        assert 'todo' in msg
        assert 'done' in msg


# ============================================================================
# TaskStateTransition (Backward Compatibility) Tests
# ============================================================================

class TestTaskStateTransition:
    """向后兼容层测试"""

    def test_can_transition_valid(self):
        """测试合法转换"""
        assert TaskStateTransition.can_transition(TaskState.BACKLOG, TaskState.TODO)
        assert TaskStateTransition.can_transition(TaskState.TODO, TaskState.IN_PROGRESS)
        assert TaskStateTransition.can_transition(TaskState.IN_PROGRESS, TaskState.IN_REVIEW)
        assert TaskStateTransition.can_transition(TaskState.IN_REVIEW, TaskState.DONE)

    def test_can_transition_invalid(self):
        """测试非法转换"""
        assert not TaskStateTransition.can_transition(TaskState.BACKLOG, TaskState.DONE)
        assert not TaskStateTransition.can_transition(TaskState.TODO, TaskState.DONE)

    def test_can_transition_same_state(self):
        """测试相同状态"""
        assert TaskStateTransition.can_transition(TaskState.TODO, TaskState.TODO)

    def test_get_allowed_transitions(self):
        """测试获取允许的目标状态"""
        allowed = TaskStateTransition.get_allowed_transitions(TaskState.TODO)
        allowed_values = {s.value for s in allowed}
        assert 'in_progress' in allowed_values
        assert 'blocked' in allowed_values
        assert 'cancelled' in allowed_values
        assert 'done' not in allowed_values

    def test_get_allowed_transitions_from_blocked(self):
        """测试 blocked 状态的允许转换"""
        allowed = TaskStateTransition.get_allowed_transitions(TaskState.BLOCKED)
        allowed_values = {s.value for s in allowed}
        assert 'todo' in allowed_values
        assert 'cancelled' in allowed_values

    def test_get_allowed_transitions_from_in_review(self):
        """测试 in_review 状态的允许转换"""
        allowed = TaskStateTransition.get_allowed_transitions(TaskState.IN_REVIEW)
        allowed_values = {s.value for s in allowed}
        assert 'done' in allowed_values
        assert 'in_progress' in allowed_values
        assert 'blocked' in allowed_values
        assert 'cancelled' in allowed_values
