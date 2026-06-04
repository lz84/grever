# -*- coding: utf-8 -*-
"""
单元测试: reins/messaging/command.py

覆盖:
1. Command / CommandResult - 基础数据类
2. CommandBus - 命令总线
3. 6 个预定义 Command 类
"""

import pytest
import sys
import asyncio
from pathlib import Path

src_dir = str(Path(__file__).parent.parent.parent / 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from reins.messaging.command import (
    Command, CommandResult, CommandBus,
    AssignTaskCommand, VerifyResultCommand,
    InstantiateScenarioCommand, DecomposeGoalCommand,
    TriggerHITLCommand, RulingCommand,
)


# ============================================================================
# Command Base Tests
# ============================================================================

class TestCommand:
    """Command 基类测试"""

    def test_auto_fields(self):
        """测试自动生成的字段"""
        cmd = Command(type='test')
        assert cmd.id.startswith('cmd-')
        assert cmd.created_at > 0
        assert cmd.trace_id.startswith('trace-')

    def test_custom_fields(self):
        """测试自定义字段"""
        cmd = Command(
            type='custom',
            payload={'key': 'value'},
            trace_id='custom-trace',
            id='cmd-custom',
        )
        assert cmd.type == 'custom'
        assert cmd.payload == {'key': 'value'}
        assert cmd.trace_id == 'custom-trace'
        assert cmd.id == 'cmd-custom'

    def test_to_dict(self):
        """测试 to_dict 序列化"""
        cmd = Command(type='test', payload={'a': 1})
        d = cmd.to_dict()
        assert d['type'] == 'test'
        assert d['payload'] == {'a': 1}
        assert d['id'] == cmd.id


class TestCommandResult:
    """CommandResult 测试"""

    def test_success_result(self):
        """测试成功结果"""
        result = CommandResult(success=True, command_id='cmd-1', data={'output': 'ok'})
        assert result.success
        assert result.error is None
        assert result.data == {'output': 'ok'}

    def test_error_result(self):
        """测试错误结果"""
        result = CommandResult(success=False, command_id='cmd-2', error='Something failed')
        assert not result.success
        assert result.error == 'Something failed'

    def test_to_dict(self):
        """测试序列化"""
        result = CommandResult(success=True, command_id='cmd-3', duration_ms=100.5)
        d = result.to_dict()
        assert d['success'] is True
        assert d['duration_ms'] == 100.5


# ============================================================================
# CommandBus Tests
# ============================================================================

class TestCommandBus:
    """命令总线测试"""

    @pytest.mark.asyncio
    async def test_register_and_dispatch(self):
        """测试注册和分发"""
        bus = CommandBus()

        async def handler(cmd):
            return CommandResult(success=True, command_id=cmd.id, data={'echo': cmd.payload})

        bus.register('echo', handler)
        result = await bus.dispatch(Command(type='echo', payload={'msg': 'hello'}))
        assert result.success
        assert result.data['echo'] == {'msg': 'hello'}

    @pytest.mark.asyncio
    async def test_no_handler(self):
        """测试无处理器时返回错误"""
        bus = CommandBus()
        result = await bus.dispatch(Command(type='unknown'))
        assert not result.success
        assert 'No handler registered' in result.error

    @pytest.mark.asyncio
    async def test_handler_exception(self):
        """测试处理器异常时捕获错误"""
        bus = CommandBus()

        async def failing_handler(cmd):
            raise RuntimeError('Handler error')

        bus.register('fail', failing_handler)
        result = await bus.dispatch(Command(type='fail'))
        assert not result.success
        assert 'Handler error' in result.error
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_middleware(self):
        """测试中间件"""
        bus = CommandBus()
        call_log = []

        class TestMiddleware:
            async def pre_dispatch(self, cmd):
                call_log.append('pre')

            async def post_dispatch(self, cmd, result):
                call_log.append('post')

            async def on_error(self, cmd, error):
                call_log.append('error')

        bus.add_middleware(TestMiddleware())

        async def handler(cmd):
            return CommandResult(success=True, command_id=cmd.id)

        bus.register('test', handler)
        await bus.dispatch(Command(type='test'))
        assert call_log == ['pre', 'post']

    @pytest.mark.asyncio
    async def test_middleware_error(self):
        """测试中间件在错误时的行为"""
        bus = CommandBus()
        call_log = []

        class ErrorMiddleware:
            async def on_error(self, cmd, error):
                call_log.append(f'error: {error}')

        bus.add_middleware(ErrorMiddleware())

        async def handler(cmd):
            raise ValueError('test error')

        bus.register('error_test', handler)
        await bus.dispatch(Command(type='error_test'))
        assert len(call_log) == 1
        assert 'test error' in call_log[0]

    @pytest.mark.asyncio
    async def test_duplicate_handler(self):
        """测试重复注册处理器抛出异常"""
        bus = CommandBus()
        async def handler(cmd):
            return CommandResult(success=True, command_id=cmd.id)

        bus.register('dup', handler)
        with pytest.raises(ValueError):
            bus.register('dup', handler)

    def test_unregister(self):
        """测试注销处理器"""
        bus = CommandBus()
        async def handler(cmd):
            return CommandResult(success=True, command_id=cmd.id)

        bus.register('remove', handler)
        assert bus.has_handler('remove')

        bus.unregister('remove')
        assert not bus.has_handler('remove')

    def test_list_commands(self):
        """测试列出已注册的命令"""
        bus = CommandBus()
        async def h1(cmd):
            return CommandResult(success=True, command_id=cmd.id)
        async def h2(cmd):
            return CommandResult(success=True, command_id=cmd.id)

        bus.register('cmd1', h1)
        bus.register('cmd2', h2)

        commands = bus.list_commands()
        assert 'cmd1' in commands
        assert 'cmd2' in commands


# ============================================================================
# Predefined Command Tests
# ============================================================================

class TestAssignTaskCommand:
    """AssignTaskCommand 测试"""

    def test_create(self):
        cmd = AssignTaskCommand(
            task_id='task-1',
            agent_id='agent-1',
            context={'priority': 'high'},
            deadline=1234567890.0,
        )
        assert cmd.type == 'assign_task'
        assert cmd.task_id == 'task-1'
        assert cmd.agent_id == 'agent-1'
        assert cmd.payload['task_id'] == 'task-1'
        assert cmd.payload['deadline'] == 1234567890.0


class TestVerifyResultCommand:
    """VerifyResultCommand 测试"""

    def test_create(self):
        cmd = VerifyResultCommand(
            task_id='task-1',
            result={'output': 'done'},
            verifier_id='verifier-1',
            verdict='approved',
        )
        assert cmd.type == 'verify_result'
        assert cmd.task_id == 'task-1'
        assert cmd.verdict == 'approved'
        assert cmd.payload['verdict'] == 'approved'


class TestInstantiateScenarioCommand:
    """InstantiateScenarioCommand 测试"""

    def test_create(self):
        cmd = InstantiateScenarioCommand(
            scenario_id='scenario-1',
            goal_id='goal-1',
            parameters={'env': 'production'},
        )
        assert cmd.type == 'instantiate_scenario'
        assert cmd.scenario_id == 'scenario-1'
        assert cmd.payload['parameters'] == {'env': 'production'}


class TestDecomposeGoalCommand:
    """DecomposeGoalCommand 测试"""

    def test_create(self):
        cmd = DecomposeGoalCommand(
            goal_id='goal-1',
            decomposition_strategy='recursive',
        )
        assert cmd.type == 'decompose_goal'
        assert cmd.goal_id == 'goal-1'
        assert cmd.decomposition_strategy == 'recursive'
        assert cmd.payload['decomposition_strategy'] == 'recursive'

    def test_default_strategy(self):
        cmd = DecomposeGoalCommand(goal_id='goal-1')
        assert cmd.decomposition_strategy == 'default'


class TestTriggerHITLCommand:
    """TriggerHITLCommand 测试"""

    def test_create(self):
        cmd = TriggerHITLCommand(
            task_id='task-1',
            input_type='file',
            required_role='admin',
        )
        assert cmd.type == 'trigger_hitl'
        assert cmd.task_id == 'task-1'
        assert cmd.input_type == 'file'
        assert cmd.required_role == 'admin'
        assert cmd.payload['input_type'] == 'file'

    def test_defaults(self):
        cmd = TriggerHITLCommand(task_id='task-1')
        assert cmd.input_type == 'form'
        assert cmd.required_role == 'human'


class TestRulingCommand:
    """RulingCommand 测试"""

    def test_create(self):
        cmd = RulingCommand(
            review_id='review-1',
            verdict='approve',
            comment='Looks good',
        )
        assert cmd.type == 'ruling'
        assert cmd.review_id == 'review-1'
        assert cmd.verdict == 'approve'
        assert cmd.comment == 'Looks good'
        assert cmd.payload['verdict'] == 'approve'
