"""Agent adapters package."""

from agent_service.adapters.base import BaseAgentAdapter, FieldDef, DispatchResult, TaskDispatch
from agent_service.adapters.registry import AgentAdapterRegistry
from agent_service.adapters.openclaw import OpenClawAdapter
from agent_service.adapters.dify import DifyAdapter
from agent_service.adapters.coze import CozeAdapter
from agent_service.adapters.claude_code import ClaudeCodeAdapter
from agent_service.adapters.codex import CodexAdapter
from agent_service.adapters.copilot import CopilotAdapter

__all__ = [
    'BaseAgentAdapter', 'FieldDef', 'DispatchResult', 'TaskDispatch',
    'AgentAdapterRegistry',
    'OpenClawAdapter', 'DifyAdapter', 'CozeAdapter',
    'ClaudeCodeAdapter', 'CodexAdapter', 'CopilotAdapter',
]
