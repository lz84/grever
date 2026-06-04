"""AdapterRegistry — 适配器注册表（工厂 + 运行时管理）"""

from typing import List, Dict, Any, Optional

from grasp.adapters.base import BaseGraspAdapter


class AdapterRegistry:
    """
    适配器注册表 — 工厂 + 运行时管理

    职责：
    1. 注册/发现所有可用适配器
    2. 按名称获取适配器实例
    3. 自动选择最佳可用后端
    4. 健康检查
    """

    def __init__(self):
        self._adapters: Dict[str, BaseGraspAdapter] = {}
        self._config: Dict[str, Dict[str, Any]] = {}

    def register(self, adapter: BaseGraspAdapter, config: Dict = None):
        """注册一个适配器"""
        self._adapters[adapter.name] = adapter
        if config:
            self._config[adapter.name] = config

    def get(self, name: str) -> BaseGraspAdapter:
        """按名称获取适配器"""
        if name not in self._adapters:
            raise KeyError(f"Adapter '{name}' not registered")
        return self._adapters[name]

    def has(self, name: str) -> bool:
        """检查适配器是否已注册"""
        return name in self._adapters

    def all(self) -> List[BaseGraspAdapter]:
        """获取所有已注册的适配器"""
        return list(self._adapters.values())

    def available(self) -> List[str]:
        """获取所有可用适配器的名称列表"""
        return [name for name, a in self._adapters.items() if a.is_available()]

    def auto_select(self) -> str:
        """
        自动选择最佳可用后端

        优先级：microsoft-graphrag > memory（兜底）
        """
        priority = ["microsoft-graphrag", "memory"]
        for name in priority:
            if name in self._adapters and self._adapters[name].is_available():
                return name
        # 兜底：返回第一个可用的
        for name in self._adapters:
            if self._adapters[name].is_available():
                return name
        return "memory"

    def get_status_all(self) -> List[Dict[str, Any]]:
        """获取所有适配器的状态"""
        return [
            {"name": a.name, "available": a.is_available(), **a.get_status()}
            for a in self._adapters.values()
        ]
