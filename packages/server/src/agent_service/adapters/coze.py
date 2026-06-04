"""
Coze Adapter — 骨架实现
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from agent_service.adapters.base import (
    BaseAgentAdapter, FieldDef, DispatchResult, TaskDispatch, TaskResult,
)


class CozeAdapter(BaseAgentAdapter):

    @property
    def platform_type(self) -> str:
        return "coze"

    @property
    def platform_label(self) -> str:
        return "Coze"

    def get_registration_fields(self) -> List[FieldDef]:
        return [
            FieldDef(
                key="bot_id", label="Bot ID", type="string",
                required=True, placeholder="7xxx",
                description="Coze Bot 的 ID",
            ),
            FieldDef(
                key="api_key", label="API Key (PAT)", type="password",
                required=True, placeholder="pat_xxx",
                description="Coze Personal Access Token",
                sensitive=True,
                validation={"min_length": 10, "pattern": r"^pat_"},
            ),
        ]

    def is_async_native(self) -> bool:
        return True

    def is_session_based(self) -> bool:
        return False

    async def register(self, agent_id: str, name: str,
                       config: Dict[str, Any]) -> str:
        # TODO: 验证 bot_id + api_key 可用
        # POST https://api.coze.com/v1/bots/{bot_id}/chat
        pass
        return agent_id

    async def unregister(self, agent_id: str, config: Dict[str, Any]) -> bool:
        return True

    async def heartbeat(self, agent_id: str, config: Dict[str, Any]) -> bool:
        # TODO: 通过 Coze API 检查 bot 状态
        pass

    async def dispatch(self, agent_id: str, config: Dict[str, Any],
                       task: TaskDispatch) -> DispatchResult:
        # TODO: POST https://api.coze.com/v1/chat
        # Body: {"bot_id": config["bot_id"], "user": task.description}
        # Headers: {"Authorization": f"Bearer {config['api_key']}"}
        pass

    async def get_result(self, dispatch_id: str,
                         config: Dict[str, Any]) -> Optional[TaskResult]:
        # TODO: 查询消息历史获取结果
        pass
