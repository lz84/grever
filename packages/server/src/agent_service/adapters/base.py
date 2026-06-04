"""
Base agent adapter — abstract interface for all platform adapters.

Defines:
- FieldDef: registration field definition
- DispatchResult: unified dispatch result
- TaskDispatch: task payload for dispatching
- BaseAgentAdapter: abstract base class all adapters must implement
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FieldDef:
    """注册表单字段定义"""
    key: str                          # 字段标识，如 'api_key'
    label: str                        # 前端显示标签，如 'API Key'
    type: str                         # string | number | password | url | select | textarea
    required: bool = False            # 是否必填
    placeholder: str = ""             # 输入框占位符
    description: str = ""             # 字段说明
    default: Any = None               # 默认值
    options: Optional[List[Dict[str, str]]] = None  # select 专用选项
    validation: Optional[Dict[str, Any]] = None     # 校验规则
    sensitive: bool = False           # 是否敏感字段（True 则 DB 加密存储）


@dataclass
class DispatchResult:
    """统一派发结果"""
    dispatch_id: str                  # 派发 ID
    status: str                       # "accepted" | "completed" | "failed"
    result: Optional[str] = None      # 执行结果（同步模式有值）
    error: Optional[str] = None       # 错误信息
    estimated_seconds: int = 0        # 预估耗时（秒）


@dataclass
class TaskDispatch:
    """派发任务载荷"""
    task_id: str
    title: str
    description: str
    context_md: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    timeout_seconds: int = 300


@dataclass
class TaskResult:
    """异步任务执行结果（get_result 返回）"""
    task_id: str
    status: str                       # "success" | "failed" | "running"
    result: Optional[str] = None
    error: Optional[str] = None


class BaseAgentAdapter(ABC):
    """所有 Agent 平台适配器的抽象基类"""

    @property
    @abstractmethod
    def platform_type(self) -> str:
        """平台类型标识，如 'openclaw', 'dify', 'coze'"""
        pass

    @property
    def platform_label(self) -> str:
        """平台显示名称，如 'OpenClaw', 'Dify'"""
        return self.platform_type

    @abstractmethod
    def get_registration_fields(self) -> List[FieldDef]:
        """返回该平台的注册字段定义"""
        pass

    @abstractmethod
    async def register(self, agent_id: str, name: str,
                       config: Dict[str, Any]) -> str:
        """
        注册/验证 Agent
        - 验证 platform_config 是否可用
        - 验证认证凭据
        - 返回 agent_id
        """
        pass

    @abstractmethod
    async def unregister(self, agent_id: str, config: Dict[str, Any]) -> bool:
        """注销 Agent"""
        pass

    @abstractmethod
    async def heartbeat(self, agent_id: str, config: Dict[str, Any]) -> bool:
        """
        发送心跳
        - 返回 True = 存活，False = 不可达
        """
        pass

    @abstractmethod
    async def dispatch(self, agent_id: str, config: Dict[str, Any],
                       task: TaskDispatch) -> DispatchResult:
        """
        派发任务到 Agent
        - 同步平台：等待完成，返回结果
        - 异步平台：立即返回 accepted + dispatch_id
        """
        pass

    @abstractmethod
    async def get_result(self, dispatch_id: str,
                         config: Dict[str, Any]) -> Optional[TaskResult]:
        """获取异步任务执行结果（异步平台专用）"""
        pass

    def is_async_native(self) -> bool:
        """
        该平台是否原生异步
        True = dispatch 立即返回，需要轮询 get_result
        默认 False（同步等待）
        """
        return False

    def is_session_based(self) -> bool:
        """
        该平台是否按会话实例化（计算节点 vs 持久 Agent）
        True: Claude Code, Codex, Copilot
        False: OpenClaw, Dify, Coze
        """
        return False

    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """校验 platform_config 是否符合该平台的 schema"""
        errors = []
        fields = self.get_registration_fields()
        for f in fields:
            if f.required and f.key not in config:
                errors.append(f"缺少必填字段: {f.label} ({f.key})")
            elif f.key in config and f.validation:
                value = str(config[f.key])
                if f.validation.get("min_length") and len(value) < f.validation["min_length"]:
                    errors.append(f"{f.label} 长度不足")
                if f.validation.get("max_length") and len(value) > f.validation["max_length"]:
                    errors.append(f"{f.label} 长度超出")
                if f.validation.get("pattern") and not re.match(f.validation["pattern"], value):
                    errors.append(f"{f.label} 格式不正确")
                if f.validation.get("url") and not self._is_valid_url(value):
                    errors.append(f"{f.label} 不是有效的 URL")
        return errors

    @staticmethod
    def _is_valid_url(value: str) -> bool:
        try:
            result = re.match(r'^https?://[^\s/$.?#].[^\s]*$', value)
            return bool(result)
        except Exception:
            return False
