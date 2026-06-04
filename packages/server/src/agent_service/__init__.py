"""
agent_service — 智能体统一注册与触发机制

门面层 + 适配层：
- adapters/: 各平台适配器（OpenClaw, Dify, Coze, Claude Code, Codex, Copilot）
- facade/: 统一门面（AgentFacade）
- poller.py: 异步派发轮询器
"""

from agent_service.adapters.registry import AgentAdapterRegistry
from agent_service.adapters.base import (
    BaseAgentAdapter, FieldDef, DispatchResult, TaskDispatch,
)
from agent_service.facade.service import AgentFacade

# Singleton instances
_registry: AgentAdapterRegistry | None = None
_facade: AgentFacade | None = None


def get_registry() -> AgentAdapterRegistry:
    """获取全局适配器注册表（懒加载，自动注册所有内置适配器）"""
    global _registry
    if _registry is None:
        _registry = AgentAdapterRegistry()
        # Auto-register all built-in adapters
        from agent_service.adapters.openclaw import OpenClawAdapter
        from agent_service.adapters.dify import DifyAdapter
        from agent_service.adapters.coze import CozeAdapter
        from agent_service.adapters.claude_code import ClaudeCodeAdapter
        from agent_service.adapters.codex import CodexAdapter
        from agent_service.adapters.copilot import CopilotAdapter
        from agent_service.adapters.hermes import HermesAdapter

        _registry.register(OpenClawAdapter())
        _registry.register(DifyAdapter())
        _registry.register(CozeAdapter())
        _registry.register(ClaudeCodeAdapter())
        _registry.register(CodexAdapter())
        _registry.register(CopilotAdapter())
        _registry.register(HermesAdapter())
    return _registry


def get_facade() -> AgentFacade:
    """获取全局门面实例"""
    global _facade
    if _facade is None:
        _facade = AgentFacade(registry=get_registry())
    return _facade
