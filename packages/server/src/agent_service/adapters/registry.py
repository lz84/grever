"""
Agent adapter registry — 注册 + 运行时路由
"""

from __future__ import annotations

from typing import Any, Dict, List

from agent_service.adapters.base import BaseAgentAdapter


class AgentAdapterRegistry:
    """Agent 适配器注册表 — 注册 + 运行时路由"""

    def __init__(self):
        self._adapters: Dict[str, BaseAgentAdapter] = {}

    def register(self, adapter: BaseAgentAdapter):
        """注册一个适配器"""
        self._adapters[adapter.platform_type] = adapter

    def get(self, platform_type: str) -> BaseAgentAdapter:
        """获取指定平台的适配器"""
        if platform_type not in self._adapters:
            raise KeyError(f"Adapter for '{platform_type}' not registered")
        return self._adapters[platform_type]

    def has(self, platform_type: str) -> bool:
        """检查是否有指定平台的适配器"""
        return platform_type in self._adapters

    def list_platforms(self) -> List[Dict[str, Any]]:
        """列出所有已注册的平台"""
        return [
            {
                "type": a.platform_type,
                "label": a.platform_label,
                "available": True,
                "is_session_based": a.is_session_based(),
            }
            for a in self._adapters.values()
        ]

    def auto_detect(self) -> str:
        """自动检测默认平台"""
        return "openclaw"
