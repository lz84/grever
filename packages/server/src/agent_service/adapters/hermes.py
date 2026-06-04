"""
HermesAdapter — Nous Research Hermes Agent API Server 适配器

Hermes API Server 提供 OpenAI 兼容接口：
  POST {base_url}/v1/chat/completions
  Headers: Authorization: Bearer {api_key}

安装：pip install hermes-agent
文档：https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server
"""

from __future__ import annotations

import httpx
from typing import Any, Dict, List

from agent_service.adapters.base import BaseAgentAdapter, DispatchResult, FieldDef


class HermesAdapter(BaseAgentAdapter):
    """Hermes Agent HTTP API 适配器（OpenAI 兼容格式）"""

    @property
    def platform_type(self) -> str:
        return "hermes"

    @property
    def platform_label(self) -> str:
        return "Hermes Agent"

    def get_registration_fields(self) -> List[FieldDef]:
        return [
            FieldDef(
                key="base_url",
                label="网关地址",
                type="text",
                required=True,
                placeholder="http://192.168.1.201:8642",
                description="Hermes API Server 地址，格式：http://IP:端口",
            ),
            FieldDef(
                key="api_key",
                label="API Key",
                type="password",
                required=True,
                placeholder="7babcae5d2e3aa370b8a47134de5f855",
                description="API_SERVER_KEY，用于认证",
                sensitive=True,
            ),
            FieldDef(
                key="model",
                label="模型",
                type="text",
                required=False,
                placeholder="anthropic/claude-sonnet-4",
                description="Hermes 使用的模型（可选，默认 hermes-agent）",
            ),
        ]

    def is_async_native(self) -> bool:
        """Hermes API 是同步的"""
        return False

    def is_session_based(self) -> bool:
        """Hermes 支持会话（但 dispatch 是无状态的）"""
        return True

    def register(self, agent_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证 Hermes 网关是否可达
        """
        base_url = config.get("base_url", "").rstrip("/")
        api_key = config.get("api_key", "")

        if not base_url:
            return {"success": False, "error": "网关地址为空"}

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{base_url}/v1/capabilities", headers={
                    "Authorization": f"Bearer {api_key}"
                })
                if resp.status_code == 200:
                    return {"success": True, "version": "ok", "capabilities": resp.json()}
                else:
                    return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except httpx.ConnectError as e:
            return {"success": False, "error": f"无法连接到 Hermes 网关：{e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def unregister(self, agent_id: str, reason: str = "") -> Dict[str, Any]:
        return {"success": True, "message": f"Agent {agent_id} 已注销（原因：{reason}）"}

    def dispatch(self, agent_id: str, config: Dict[str, Any], task: Dict[str, Any]) -> DispatchResult:
        """
        通过 HTTP POST /v1/chat/completions 向 Hermes 派发任务

        请求体（OpenAI 格式）：
            {
              "model": "hermes-agent",
              "messages": [{"role": "user", "content": "<prompt>"}],
              "stream": false
            }
        """
        base_url = config.get("base_url", "").rstrip("/")
        api_key = config.get("api_key", "")

        if not base_url:
            return DispatchResult(
                success=False,
                error="Hermes 网关地址为空",
                output="",
            )

        prompt = task.get("prompt", task.get("content", ""))
        if not prompt:
            return DispatchResult(
                success=False,
                error="任务内容为空",
                output="",
            )

        # 构建 OpenAI 格式请求
        model = config.get("model", "hermes-agent")
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            timeout = task.get("timeout", 600.0)
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(
                    f"{base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )
                data = resp.json()

                if resp.status_code == 200 and data.get("choices"):
                    content = data["choices"][0]["message"]["content"]
                    return DispatchResult(
                        dispatch_id=data.get("id", f"hermes-{agent_id[:8]}"),
                        status="completed",
                        result=content,
                    )
                else:
                    error_msg = data.get("error", {}).get("message", str(data))
                    return DispatchResult(
                        dispatch_id=f"hermes-{agent_id[:8]}",
                        status="failed",
                        error=error_msg,
                    )
        except httpx.ReadTimeout:
            return DispatchResult(
                dispatch_id=f"hermes-{agent_id[:8]}",
                status="failed",
                error="Hermes 网关响应超时",
            )
        except httpx.ConnectError as e:
            return DispatchResult(
                dispatch_id=f"hermes-{agent_id[:8]}",
                status="failed",
                error=f"无法连接到 Hermes 网关：{e}",
            )
        except Exception as e:
            return DispatchResult(
                dispatch_id=f"hermes-{agent_id[:8]}",
                status="failed",
                error=str(e),
            )

    def heartbeat(self, agent_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """检查 Hermes 网关是否在线"""
        base_url = config.get("base_url", "").rstrip("/")
        api_key = config.get("api_key", "")

        if not base_url:
            return {"status": "offline", "error": "网关地址为空"}

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{base_url}/v1/capabilities", headers={
                    "Authorization": f"Bearer {api_key}"
                })
                if resp.status_code == 200:
                    return {
                        "status": "online",
                        "model": config.get("model", "hermes-agent"),
                    }
                return {"status": "offline", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "offline", "error": str(e)}

    def get_result(self, dispatch_id: str, agent_id: str) -> DispatchResult | None:
        """Hermes API 是同步的，dispatch() 已返回结果"""
        return None
