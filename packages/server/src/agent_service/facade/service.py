"""
AgentFacade — 智能体统一门面层

所有数据读写通过 Nexus REST API，不直接操作数据库：
- GET /api/v1/agents/{id}      → 获取 agent 信息
- POST /api/v1/agents          → 注册 agent
- DELETE /api/v1/agents/{id}  → 删除 agent
- POST /api/v1/agents/{id}/heartbeat → 心跳
- POST /api/v1/tasks/{id}/complete   → 完成任务（复用 dispatch_coordinator.py 模式）
"""

from __future__ import annotations

import json
import requests
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger

from agent_service.adapters.base import (
    BaseAgentAdapter, DispatchResult, TaskDispatch,
)
from agent_service.adapters.registry import AgentAdapterRegistry


# ── API base URL ─────────────────────────────────────────────────────────────
_API_BASE = "http://127.0.0.1:8097"


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class AgentRegisterRequest:
    """注册请求"""
    agent_id: str
    name: str
    platform_type: str = "openclaw"
    capability_tags: Dict[str, List[str]] = None
    platform_config: Optional[Dict[str, Any]] = None
    model_name: Optional[str] = None
    trigger_mode: str = "sse"


@dataclass
class AgentRegistered:
    """注册响应"""
    agent_id: str
    status: str
    platform_type: str


@dataclass
class HeartbeatResult:
    """心跳响应"""
    agent_id: str
    alive: bool
    load: Optional[int] = None
    current_tasks: Optional[int] = None


# ── AgentFacade ───────────────────────────────────────────────────────────────

class AgentFacade:
    """
    Agent 服务门面 — 统一入口

    调度层（Reins/Grasp/Evo）通过此类访问 Agent 服务。
    所有数据操作通过 Nexus API，不直接访问数据库。
    """

    def __init__(self, registry: AgentAdapterRegistry):
        self._registry = registry

    # ── Platform listing ──────────────────────────────────────────────────

    def list_platforms(self) -> List[Dict[str, Any]]:
        """列出所有已注册的平台"""
        return self._registry.list_platforms()

    def get_registration_schema(self, platform_type: str) -> Dict[str, Any]:
        """获取指定平台的注册 schema"""
        adapter = self._registry.get(platform_type)
        return {
            "platform_type": adapter.platform_type,
            "platform_label": adapter.platform_label,
            "is_session_based": adapter.is_session_based(),
            "fields": [
                {
                    "key": f.key,
                    "label": f.label,
                    "type": f.type,
                    "required": f.required,
                    "placeholder": f.placeholder,
                    "description": f.description,
                    "default": f.default,
                    "options": f.options,
                    "validation": f.validation,
                    "sensitive": f.sensitive,
                }
                for f in adapter.get_registration_fields()
            ],
        }

    # ── Agent CRUD (via Nexus API) ───────────────────────────────────────

    async def register(self, request: AgentRegisterRequest) -> AgentRegistered:
        """
        注册 Agent

        流程：
        1. 获取对应平台的 adapter
        2. 校验 platform_config 符合 schema
        3. adapter.register() 做目标平台验证
        4. 通过 POST /api/v1/agents 写 agents 表
        5. 通过 POST /api/v1/agents/{id}/config 写 agents_config 表（如果实现了）
        """
        adapter = self._registry.get(request.platform_type)
        config = request.platform_config or {}

        # 校验 platform_config
        errors = adapter.validate_config(config)
        if errors:
            raise ValueError(f"平台配置校验失败: {'; '.join(errors)}")

        # ── 连通性验证：先调 adapter.register() 验证目标平台是否可达 ──
        try:
            agent_id = await adapter.register(
                request.agent_id, request.name, config,
            )
        except Exception as e:
            logger.error(f"[AgentFacade] adapter.register connectivity check failed: {e}")
            raise RuntimeError(
                f"目标平台连通性验证失败: {request.platform_type} — {e}"
            ) from e
        if not agent_id:
            raise RuntimeError(
                f"目标平台注册返回空 agent_id: {request.platform_type}"
            )

        # ── 连通性验证通过，再通过 Nexus API 注册到 DB ──
        caps = request.capability_tags or {
            "business": [], "professional": [], "technical": [], "management": [],
        }

        payload = {
            "agent_id": request.agent_id,
            "name": request.name,
            "capability_tags": caps,
            "trigger_mode": request.trigger_mode,
            "model_name": request.model_name or "",
            # 新字段（后端需要支持）
            "platform_type": request.platform_type,
        }

        try:
            resp = requests.post(
                f"{_API_BASE}/api/v1/agents",
                json=payload,
                timeout=15,
            )
            if resp.status_code not in (200, 201):
                logger.error(f"[AgentFacade] register API failed: {resp.status_code} {resp.text}")
                # 不阻止流程，agent 已在平台验证通过
        except Exception as e:
            logger.warning(f"[AgentFacade] register API call failed: {e}")

        return AgentRegistered(
            agent_id=agent_id,
            status="online",
            platform_type=request.platform_type,
        )

    async def unregister(self, agent_id: str, reason: str = None) -> bool:
        """
        注销 Agent

        流程：
        1. 通过 GET /api/v1/agents/{id} 获取 agent 信息
        2. 获取对应 adapter，调用 unregister
        3. 通过 DELETE /api/v1/agents/{id} 删除
        """
        # 获取 agent 信息（含 platform_type）
        agent_info = self._get_agent_from_api(agent_id)
        if not agent_info:
            return False

        platform_type = agent_info.get("platform_type", "openclaw")

        # 获取 platform_config
        config = self._get_agent_config_from_api(agent_id) or {}

        # 调用 adapter.unregister
        try:
            adapter = self._registry.get(platform_type)
            await adapter.unregister(agent_id, config)
        except Exception as e:
            logger.warning(f"[AgentFacade] adapter.unregister error: {e}")

        # 通过 API 删除
        try:
            params = {"reason": reason} if reason else {}
            resp = requests.delete(
                f"{_API_BASE}/api/v1/agents/{agent_id}",
                params=params,
                timeout=10,
            )
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(f"[AgentFacade] delete API failed: {e}")
            return False

    async def heartbeat(self, agent_id: str,
                        status: Optional[Dict[str, Any]] = None) -> HeartbeatResult:
        """
        Agent 心跳

        流程：
        1. 获取 agent 信息
        2. 调 adapter.heartbeat() 验证存活
        3. 通过 POST /api/v1/agents/{id}/heartbeat 同步到 DB
        """
        agent_info = self._get_agent_from_api(agent_id)
        if not agent_info:
            return HeartbeatResult(agent_id=agent_id, alive=False)

        platform_type = agent_info.get("platform_type", "openclaw")
        config = self._get_agent_config_from_api(agent_id) or {}

        # 平台心跳检测
        try:
            adapter = self._registry.get(platform_type)
            alive = await adapter.heartbeat(agent_id, config)
        except Exception as e:
            logger.warning(f"[AgentFacade] adapter.heartbeat error: {e}")
            alive = False

        # 同步到 DB
        if alive:
            try:
                requests.post(
                    f"{_API_BASE}/api/v1/agents/{agent_id}/heartbeat",
                    json=status or {},
                    timeout=10,
                )
            except Exception as e:
                logger.warning(f"[AgentFacade] heartbeat API call failed: {e}")

        return HeartbeatResult(
            agent_id=agent_id,
            alive=alive,
            load=status.get("load") if status else None,
            current_tasks=status.get("current_tasks") if status else None,
        )

    async def dispatch(self, agent_id: str,
                       task: TaskDispatch) -> DispatchResult:
        """
        派发任务

        流程：
        1. GET /api/v1/agents/{id} → 获取 platform_type + config
        2. 调 adapter.dispatch()
        3. 返回结果（同步直接返回，异步返回 accepted + dispatch_id）
        """
        agent_info = self._get_agent_from_api(agent_id)
        if not agent_info:
            return DispatchResult(
                dispatch_id=task.task_id,
                status="failed",
                error=f"Agent {agent_id} not found",
            )

        platform_type = agent_info.get("platform_type", "openclaw")
        config = self._get_agent_config_from_api(agent_id) or {}

        try:
            adapter = self._registry.get(platform_type)
            result = await adapter.dispatch(agent_id, config, task)
            return result
        except Exception as e:
            logger.error(f"[AgentFacade] dispatch error: {e}")
            return DispatchResult(
                dispatch_id=task.task_id,
                status="failed",
                error=str(e),
            )

    async def get_result(self, dispatch_id: str,
                         agent_id: str) -> Optional[DispatchResult]:
        """获取异步任务执行结果"""
        agent_info = self._get_agent_from_api(agent_id)
        if not agent_info:
            return None

        platform_type = agent_info.get("platform_type", "openclaw")
        config = self._get_agent_config_from_api(agent_id) or {}

        try:
            adapter = self._registry.get(platform_type)
            return await adapter.get_result(dispatch_id, config)
        except Exception as e:
            logger.error(f"[AgentFacade] get_result error: {e}")
            return None

    async def complete_task(self, task_id: str, result_text: str,
                            success: bool = True) -> bool:
        """
        完成任务（通过 API 调用 complete_task 端点）

        复用 dispatch_coordinator.py 的模式。
        """
        payload = {
            "status": "done" if success else "failed",
            "result": result_text[:500] if result_text else "No result",
        }
        try:
            resp = requests.post(
                f"{_API_BASE}/api/v1/tasks/{task_id}/complete",
                json=payload,
                timeout=30,
            )
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(f"[AgentFacade] complete_task failed: {e}")
            return False

    # ── Internal helpers (API calls) ───────────────────────────────────────

    def _get_agent_from_api(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """通过 API 获取 agent 信息"""
        try:
            resp = requests.get(
                f"{_API_BASE}/api/v1/agents/{agent_id}",
                timeout=10,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"[AgentFacade] _get_agent_from_api error: {e}")
            return None

    def _get_agent_config_from_api(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """通过 API 获取 agent 的 platform_config"""
        # 目前 agents API 还没有单独返回 config_json 的端点
        # 从 agents 表的 metadata/address/trigger_mode 等字段构建
        agent_info = self._get_agent_from_api(agent_id)
        if not agent_info:
            return None

        config = {}
        meta = agent_info.get("metadata", {})
        if isinstance(meta, dict):
            config.update(meta)
        addr = agent_info.get("address")
        if addr:
            config["address"] = addr
        tm = agent_info.get("trigger_mode")
        if tm:
            config["trigger_mode"] = tm
        model = agent_info.get("model_name")
        if model:
            config["model"] = model

        return config

    def _save_agent_config(self, agent_id: str,
                            platform_type: str,
                            config: Dict[str, Any]) -> bool:
        """
        保存 agents_config（通过 API 或直接 DB）

        目前 API 尚未暴露 agents_config 端点，
        暂时直接写 DB（待后续 API 实现后改为 API 调用）。
        这里通过 requests 请求自定义端点。
        """
        # TODO: 后续 /api/v1/agents/{id}/config 端点实现后改为 API 方式
        # 目前先尝试通过内部 API 保存，如果端点不存在则跳过
        try:
            resp = requests.post(
                f"{_API_BASE}/api/v1/agents/{agent_id}/config",
                json={"platform_type": platform_type, "config_json": json.dumps(config)},
                timeout=10,
            )
            return resp.status_code in (200, 201, 404)  # 404=端点未实现，容忍
        except Exception as e:
            logger.warning(f"[AgentFacade] _save_agent_config failed: {e}")
            return False