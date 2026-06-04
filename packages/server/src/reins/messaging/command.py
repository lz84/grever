"""Nexus Command Bus — 命令分发总线"""
import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Callable, Type, Awaitable

@dataclass
class Command:
    """命令基类"""
    type: str                                    # 命令类型 (assign_task/verify_result/...)
    payload: Dict[str, Any] = field(default_factory=dict)
    trace_id: str = ''
    id: str = ''
    created_at: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = 'cmd-' + uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = time.time()
        if not self.trace_id:
            self.trace_id = 'trace-' + uuid.uuid4().hex[:8]

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class CommandResult:
    """命令执行结果"""
    success: bool
    command_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

# 命令处理器类型
CommandHandler = Callable[[Command], Awaitable[CommandResult]]

class CommandBus:
    """
    命令总线 — 分发命令到注册的处理器

    用法:
        bus = CommandBus()
        bus.register('assign_task', handle_assign_task)
        result = await bus.dispatch(Command(type='assign_task', payload={...}))
    """

    def __init__(self):
        self._handlers: Dict[str, CommandHandler] = {}
        self._middleware: list = []

    def register(self, command_type: str, handler: CommandHandler):
        """注册命令处理器"""
        if command_type in self._handlers:
            raise ValueError(f'Handler already registered for command type: {command_type}')
        self._handlers[command_type] = handler

    def unregister(self, command_type: str):
        """注销命令处理器"""
        self._handlers.pop(command_type, None)

    def add_middleware(self, middleware: Callable):
        """添加中间件 (logging, metrics, etc.)"""
        self._middleware.append(middleware)

    async def dispatch(self, command: Command) -> CommandResult:
        """
        分发命令到处理器

        Args:
            command: 要执行的命令

        Returns:
            CommandResult: 执行结果

        Raises:
            ValueError: 如果没有注册的处理器
        """
        handler = self._handlers.get(command.type)
        if not handler:
            return CommandResult(
                success=False,
                command_id=command.id,
                error=f'No handler registered for command type: {command.type}',
            )

        start = time.time()

        # 执行中间件 (pre)
        for mw in self._middleware:
            if hasattr(mw, 'pre_dispatch'):
                await mw.pre_dispatch(command)

        try:
            result = await handler(command)
            result.duration_ms = (time.time() - start) * 1000
            result.command_id = command.id

            # 执行中间件 (post)
            for mw in self._middleware:
                if hasattr(mw, 'post_dispatch'):
                    await mw.post_dispatch(command, result)

            return result
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            # 执行中间件 (error)
            for mw in self._middleware:
                if hasattr(mw, 'on_error'):
                    await mw.on_error(command, e)

            return CommandResult(
                success=False,
                command_id=command.id,
                error=str(e),
                duration_ms=duration_ms,
            )

    def list_commands(self) -> list:
        """列出所有已注册的命令类型"""
        return list(self._handlers.keys())

    def has_handler(self, command_type: str) -> bool:
        """检查是否有处理器"""
        return command_type in self._handlers

# ============================================================
# 预定义的 Command 类型 (Phase 3 实现具体 handler)
# ============================================================

# ============================================================================
# 预定义的 Command 类型 (Phase 3 实现具体 handler)
# ============================================================================

@dataclass
class AssignTaskCommand(Command):
    """派发任务给 Agent"""
    type: str = 'assign_task'
    task_id: str = ''
    agent_id: str = ''
    context: Dict[str, Any] = field(default_factory=dict)
    deadline: float = 0.0

    def __post_init__(self):
        if not hasattr(self, 'id') or not self.id:
            self.id = 'cmd-' + uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = time.time()
        if not self.trace_id:
            self.trace_id = 'trace-' + uuid.uuid4().hex[:8]
        self.payload = {
            'task_id': self.task_id,
            'agent_id': self.agent_id,
            'context': self.context,
            'deadline': self.deadline,
        }


@dataclass
class VerifyResultCommand(Command):
    """验证任务结果"""
    type: str = 'verify_result'
    task_id: str = ''
    result: Dict[str, Any] = field(default_factory=dict)
    verifier_id: str = ''
    verdict: str = ''  # approved / rejected / needs_revision

    def __post_init__(self):
        if not hasattr(self, 'id') or not self.id:
            self.id = 'cmd-' + uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = time.time()
        if not self.trace_id:
            self.trace_id = 'trace-' + uuid.uuid4().hex[:8]
        self.payload = {
            'task_id': self.task_id,
            'result': self.result,
            'verifier_id': self.verifier_id,
            'verdict': self.verdict,
        }


@dataclass
class InstantiateScenarioCommand(Command):
    """实例化场景"""
    type: str = 'instantiate_scenario'
    scenario_id: str = ''
    goal_id: str = ''
    parameters: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not hasattr(self, 'id') or not self.id:
            self.id = 'cmd-' + uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = time.time()
        if not self.trace_id:
            self.trace_id = 'trace-' + uuid.uuid4().hex[:8]
        self.payload = {
            'scenario_id': self.scenario_id,
            'goal_id': self.goal_id,
            'parameters': self.parameters,
        }


@dataclass
class DecomposeGoalCommand(Command):
    """分解目标"""
    type: str = 'decompose_goal'
    goal_id: str = ''
    decomposition_strategy: str = 'default'  # default / recursive / parallel

    def __post_init__(self):
        if not hasattr(self, 'id') or not self.id:
            self.id = 'cmd-' + uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = time.time()
        if not self.trace_id:
            self.trace_id = 'trace-' + uuid.uuid4().hex[:8]
        self.payload = {
            'goal_id': self.goal_id,
            'decomposition_strategy': self.decomposition_strategy,
        }


@dataclass
class TriggerHITLCommand(Command):
    """触发人机协同"""
    type: str = 'trigger_hitl'
    task_id: str = ''
    input_type: str = 'form'  # form / text / file / custom
    required_role: str = 'human'  # human / admin / expert

    def __post_init__(self):
        if not hasattr(self, 'id') or not self.id:
            self.id = 'cmd-' + uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = time.time()
        if not self.trace_id:
            self.trace_id = 'trace-' + uuid.uuid4().hex[:8]
        self.payload = {
            'task_id': self.task_id,
            'input_type': self.input_type,
            'required_role': self.required_role,
        }


@dataclass
class RulingCommand(Command):
    """人工裁决"""
    type: str = 'ruling'
    review_id: str = ''
    verdict: str = ''  # approve / reject / escalate / revise
    comment: str = ''

    def __post_init__(self):
        if not hasattr(self, 'id') or not self.id:
            self.id = 'cmd-' + uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = time.time()
        if not self.trace_id:
            self.trace_id = 'trace-' + uuid.uuid4().hex[:8]
        self.payload = {
            'review_id': self.review_id,
            'verdict': self.verdict,
            'comment': self.comment,
        }
