"""
Dify Adapter — 骨架实现

get_registration_fields() 已完整实现，dispatch/get_result/heartbeat 留 TODO。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from agent_service.adapters.base import (
    BaseAgentAdapter, FieldDef, DispatchResult, TaskDispatch, TaskResult,
)


class DifyAdapter(BaseAgentAdapter):

    @property
    def platform_type(self) -> str:
        return "dify"

    @property
    def platform_label(self) -> str:
        return "Dify"

    def get_registration_fields(self) -> List[FieldDef]:
        return [
            FieldDef(
                key="base_url", label="API Base URL", type="url",
                required=True, placeholder="https://api.dify.ai",
                description="Dify 实例的 API 地址",
                validation={"url": True},
            ),
            FieldDef(
                key="api_key", label="API Key", type="password",
                required=True, placeholder="app-xxx",
                description="Dify 应用的 API Key",
                sensitive=True,
                validation={"min_length": 20, "pattern": r"^app-"},
            ),
            FieldDef(
                key="app_id", label="应用 ID", type="string",
                required=True, placeholder="workflow-xxx",
                description="Dify Workflow 或 Chatflow 的 ID",
            ),
        ]

    def is_async_native(self) -> bool:
        return False

    def is_session_based(self) -> bool:
        return False

    async def register(self, agent_id: str, name: str,
                       config: Dict[str, Any]) -> str:
        # TODO: 验证连通性 GET {base_url}/health + 凭据验证
        # import aiohttp
        # async with aiohttp.ClientSession() as session:
        #     async with session.get(f"{config['base_url']}/health") as resp:
        #         if resp.status != 200:
        #             raise ValueError(f"Dify health check failed: {resp.status}")
        pass
        return agent_id

    async def unregister(self, agent_id: str, config: Dict[str, Any]) -> bool:
        # TODO: Dify 无需特殊注销操作
        return True

    async def heartbeat(self, agent_id: str, config: Dict[str, Any]) -> bool:
        # TODO: 1. GET {base_url}/health → 200 验证服务可用性
        #       2. 可选：发送最小 workflow test 验证 api_key + app_id 有效
        pass

    async def dispatch(self, agent_id: str, config: Dict[str, Any],
                       task: TaskDispatch) -> DispatchResult:
        # TODO: POST {base_url}/v1/workflows/run
        # Body: {"inputs": {"task": task.description}, "response_mode": "blocking"}
        # Headers: {"Authorization": f"Bearer {config['api_key']}"}
        pass

    async def get_result(self, dispatch_id: str,
                         config: Dict[str, Any]) -> Optional[TaskResult]:
        # TODO: GET {base_url}/v1/workflows/tasks/{dispatch_id}
        pass
