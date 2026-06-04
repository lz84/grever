"""
Claude Code Adapter — session-based 计算节点
"""

from __future__ import annotations

import subprocess
from typing import Any, Dict, List, Optional

from loguru import logger

from agent_service.adapters.base import (
    BaseAgentAdapter, FieldDef, DispatchResult, TaskDispatch, TaskResult,
)


class ClaudeCodeAdapter(BaseAgentAdapter):

    @property
    def platform_type(self) -> str:
        return "claude_code"

    @property
    def platform_label(self) -> str:
        return "Claude Code"

    def get_registration_fields(self) -> List[FieldDef]:
        return [
            FieldDef(
                key="claude_binary", label="Claude Code 路径", type="string",
                required=True, default="claude",
                description="Claude Code CLI 路径，默认 claude（PATH 中）",
            ),
            FieldDef(
                key="workspace", label="工作区", type="string",
                required=True, placeholder="/path/to/project",
                description="Claude Code 执行时的工作目录",
            ),
            FieldDef(
                key="model", label="模型", type="string",
                required=False, placeholder="claude-sonnet-4-20250514",
                description="使用的 Claude 模型",
            ),
        ]

    def is_async_native(self) -> bool:
        return False

    def is_session_based(self) -> bool:
        return True

    async def register(self, agent_id: str, name: str,
                       config: Dict[str, Any]) -> str:
        # 验证 claude CLI 可用
        binary = config.get("claude_binary", "claude")
        try:
            result = subprocess.run(
                [binary, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            logger.info(f"[ClaudeCodeAdapter] CLI version: {result.stdout.strip()}")
        except FileNotFoundError:
            raise RuntimeError(f"{binary} not found in PATH")
        return agent_id

    async def unregister(self, agent_id: str, config: Dict[str, Any]) -> bool:
        return True

    async def heartbeat(self, agent_id: str, config: Dict[str, Any]) -> bool:
        binary = config.get("claude_binary", "claude")
        try:
            result = subprocess.run(
                [binary, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"[ClaudeCodeAdapter] Heartbeat failed: {e}")
            return False

    async def dispatch(self, agent_id: str, config: Dict[str, Any],
                       task: TaskDispatch) -> DispatchResult:
        # TODO: 确定工作区路径中是否有 ANTHROPIC_API_KEY
        # subprocess.run([binary, "-p", task.description,
        #                 "--allow-all", "--yolo", "--add-dir", config["workspace"]])
        pass

    async def get_result(self, dispatch_id: str,
                         config: Dict[str, Any]) -> Optional[TaskResult]:
        # TODO: 从 stdout 捕获结果
        pass