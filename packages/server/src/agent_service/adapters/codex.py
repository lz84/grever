"""
Codex Adapter — session-based 计算节点
"""

from __future__ import annotations

import subprocess
from typing import Any, Dict, List, Optional

from loguru import logger

from agent_service.adapters.base import (
    BaseAgentAdapter, FieldDef, DispatchResult, TaskDispatch, TaskResult,
)


class CodexAdapter(BaseAgentAdapter):

    @property
    def platform_type(self) -> str:
        return "codex"

    @property
    def platform_label(self) -> str:
        return "Codex"

    def get_registration_fields(self) -> List[FieldDef]:
        return [
            FieldDef(
                key="workspace", label="工作区", type="string",
                required=True, placeholder="/path/to/project",
                description="Codex 执行时的工作目录",
            ),
            FieldDef(
                key="model", label="模型", type="string",
                required=False, placeholder="o3",
                description="使用的 Codex 模型",
            ),
        ]

    def is_async_native(self) -> bool:
        return False

    def is_session_based(self) -> bool:
        return True

    async def register(self, agent_id: str, name: str,
                       config: Dict[str, Any]) -> str:
        binary = "codex"
        try:
            result = subprocess.run(
                [binary, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            logger.info(f"[CodexAdapter] CLI version: {result.stdout.strip()}")
        except FileNotFoundError:
            raise RuntimeError(f"{binary} not found in PATH")
        return agent_id

    async def unregister(self, agent_id: str, config: Dict[str, Any]) -> bool:
        return True

    async def heartbeat(self, agent_id: str, config: Dict[str, Any]) -> bool:
        try:
            result = subprocess.run(
                ["codex", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"[CodexAdapter] Heartbeat failed: {e}")
            return False

    async def dispatch(self, agent_id: str, config: Dict[str, Any],
                       task: TaskDispatch) -> DispatchResult:
        # TODO: subprocess.run(["codex", "run", "-p", task.description,
        #                 "--work-dir", config["workspace"]])
        pass

    async def get_result(self, dispatch_id: str,
                         config: Dict[str, Any]) -> Optional[TaskResult]:
        pass