"""
Nexus Reins Grasp 调用器
负责与 Grasp 服务通信，支持熔断 + 优雅降级

架构:
    GraspClient
        ├── CircuitBreaker (熔断器)
        │   ├── CLOSED → 正常调用 Grasp 服务
        │   ├── OPEN → 快速失败，走本地降级
        │   └── HALF_OPEN → 试探性恢复检测
        │
        └── GraspFallbackEngine (本地降级引擎)
            ├── 意图理解 → 正则模板匹配
            ├── 智能体匹配 → 能力标签匹配
            ├── 认知抽取 → 本地关键词检索
            └── 认知反馈 → 本地缓存记录
"""

import asyncio
import httpx
import json
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from reins.common.grasp_client.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpen
from reins.common.grasp_client.fallback import GraspFallbackEngine

class GraspCapability(str, Enum):
    INTENT_UNDERSTANDING = "intent_understanding"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    AGENT_MATCHING = "agent_matching"
    COGNITIVE_FEEDBACK = "cognitive_feedback"
    DISPATCH_COGNITION = "dispatch_cognition"

class GraspCallError(Exception):
    """Grasp 调用异常"""
    pass

class GraspCallRequest(BaseModel):
    """Grasp 调用请求"""
    capability: GraspCapability
    payload: Dict[str, Any]
    timeout_seconds: float = 5.0
    retry_count: int = 0
    callback_url: Optional[str] = None

class GraspCallResponse(BaseModel):
    """Grasp 调用响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    cache_hit: bool = False
    duration_ms: int = 0
    fallback: bool = False  # 新增: 是否使用了降级方案
    fallback_source: Optional[str] = None  # 新增: 降级来源

class IGraspClient(ABC):
    """Grasp 客户端接口"""
    
    @abstractmethod
    async def call_intent_understanding(
        self,
        user_goal: str,
        context: Dict[str, Any]
    ) -> GraspCallResponse:
        """意图理解 - 同步调用"""
        pass
    
    @abstractmethod
    async def call_agent_matching(
        self,
        task_requirements: Dict[str, Any],
        available_agents: List[Dict[str, Any]]
    ) -> GraspCallResponse:
        """智能体匹配 - 同步调用"""
        pass

    @abstractmethod
    async def call_dispatch_cognition(
        self,
        task_id: str,
        task_title: str,
        task_description: str,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
        max_cognitions: int = 5
    ) -> GraspCallResponse:
        """任务派发时认知抽取 - 同步调用"""
        pass
    
    @abstractmethod
    async def send_cognitive_feedback(
        self,
        task_id: str,
        execution_result: Dict[str, Any],
        learnings: Dict[str, Any]
    ) -> bool:
        """认知回流 - 异步调用"""
        pass
    
    @abstractmethod
    async def send_execution_monitoring(
        self,
        task_id: str,
        execution_state: Dict[str, Any],
        callbacks: Dict[str, str]
    ) -> bool:
        """执行监控 - 异步调用"""
        pass
    
    @abstractmethod
    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        pass

class GraspClient(IGraspClient):
    """
    Grasp 客户端实现 (带熔断 + 优雅降级)
    
    当 Grasp 服务不可用时:
    1. 熔断器快速失败 (不等待超时)
    2. 本地降级引擎提供规则-based 替代方案
    3. 熔断器定期试探恢复
    
    配置环境变量:
        GRASP_BASE_URL: Grasp 服务地址 (默认 http://grasp:8000)
        GRASP_CB_FAILURE_THRESHOLD: 熔断失败阈值 (默认 3)
        GRASP_CB_RECOVERY_TIMEOUT_MS: 恢复超时毫秒 (默认 30000)
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    ):
        self._base_url = base_url or os.environ.get("GRASP_BASE_URL", "http://grasp:8000")
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            follow_redirects=True,
        )
        
        # 熔断器
        cb_config = circuit_breaker_config or CircuitBreakerConfig(
            failure_threshold=int(os.environ.get("GRASP_CB_FAILURE_THRESHOLD", "3")),
            recovery_timeout_ms=int(os.environ.get("GRASP_CB_RECOVERY_TIMEOUT_MS", "30000")),
        )
        self._circuit_breaker = CircuitBreaker(cb_config)
        
        # 本地降级引擎
        self._fallback = GraspFallbackEngine()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.aclose()
    
    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        return self._circuit_breaker.stats
    
    def reload_fallback_knowledge(self):
        """重新加载本地降级知识库"""
        self._fallback.reload()
    
    # === 意图理解 ===
    
    async def call_intent_understanding(
        self,
        user_goal: str,
        context: Dict[str, Any]
    ) -> GraspCallResponse:
        """意图理解 - 通过熔断器调用，失败时本地降级"""
        import time
        
        def _call_remote():
            return self._call_remote_intent_understanding(user_goal, context)
        
        def _fallback_fn():
            result = self._fallback.intent_understanding(user_goal, context)
            return GraspCallResponse(
                success=True,
                data=result,
                fallback=True,
                fallback_source="local_template_engine",
                duration_ms=0,
            )
        
        try:
            return await self._circuit_breaker.call(
                _call_remote,
                fallback=_fallback_fn,
            )
        except CircuitBreakerOpen as e:
            # 熔断器已打开，直接使用降级
            result = self._fallback.intent_understanding(user_goal, context)
            return GraspCallResponse(
                success=True,
                data=result,
                fallback=True,
                fallback_source="local_template_engine",
                duration_ms=0,
            )
    
    async def _call_remote_intent_understanding(
        self,
        user_goal: str,
        context: Dict[str, Any]
    ) -> GraspCallResponse:
        """远程调用意图理解"""
        request_data = {
            "user_goal": user_goal,
            "context": context,
            "options": {
                "max_tasks": 10,
                "include_templates": True
            }
        }
        
        try:
            response = await self._client.post(
                f"{self._base_url}/api/v1/grasp/intent",
                json=request_data,
                timeout=5.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return GraspCallResponse(
                    success=True,
                    data=data,
                    cache_hit=data.get("cache_hit", False),
                    duration_ms=response.elapsed.microseconds // 1000
                )
            elif response.status_code == 503:
                data = response.json()
                return GraspCallResponse(
                    success=True,
                    data=data.get("fallback_data", {}),
                    cache_hit=False,
                    duration_ms=response.elapsed.microseconds // 1000,
                    error="Grasp service degraded",
                    fallback=True,
                    fallback_source="grasp_503",
                )
            else:
                # 其他 HTTP 错误，抛出异常让熔断器捕获
                raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
        except (httpx.ConnectError, httpx.TimeoutException):
            raise  # 让熔断器捕获
        except Exception:
            raise  # 让熔断器捕获所有异常
    
    # === 智能体匹配 ===
    
    async def call_agent_matching(
        self,
        task_requirements: Dict[str, Any],
        available_agents: List[Dict[str, Any]]
    ) -> GraspCallResponse:
        """智能体匹配 - 通过熔断器调用，失败时本地降级"""
        def _call_remote():
            return self._call_remote_agent_matching(task_requirements, available_agents)
        
        def _fallback_fn():
            result = self._fallback.agent_matching(task_requirements, available_agents)
            return GraspCallResponse(
                success=True,
                data=result,
                fallback=True,
                fallback_source="local_capability_matching",
                duration_ms=0,
            )
        
        try:
            return await self._circuit_breaker.call(
                _call_remote,
                fallback=_fallback_fn,
            )
        except CircuitBreakerOpen:
            result = self._fallback.agent_matching(task_requirements, available_agents)
            return GraspCallResponse(
                success=True,
                data=result,
                fallback=True,
                fallback_source="local_capability_matching",
                duration_ms=0,
            )
    
    async def _call_remote_agent_matching(
        self,
        task_requirements: Dict[str, Any],
        available_agents: List[Dict[str, Any]]
    ) -> GraspCallResponse:
        """远程调用智能体匹配"""
        request_data = {
            "task_requirements": task_requirements,
            "available_agents": available_agents
        }
        
        try:
            response = await self._client.post(
                f"{self._base_url}/api/v1/grasp/agent-match",
                json=request_data,
                timeout=2.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return GraspCallResponse(
                    success=True,
                    data=data,
                    cache_hit=data.get("cache_hit", False),
                    duration_ms=response.elapsed.microseconds // 1000
                )
            else:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
        except (httpx.ConnectError, httpx.TimeoutException):
            raise
        except Exception:
            raise
    
    # === 认知抽取 ===
    
    async def call_dispatch_cognition(
        self,
        task_id: str,
        task_title: str,
        task_description: str,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
        max_cognitions: int = 5
    ) -> GraspCallResponse:
        """任务认知抽取 - 通过熔断器调用，失败时本地降级"""
        def _call_remote():
            return self._call_remote_dispatch_cognition(
                task_id, task_title, task_description, task_type, context, max_cognitions
            )
        
        def _fallback_fn():
            result = self._fallback.dispatch_cognition(
                task_id, task_title, task_description, task_type, context, max_cognitions
            )
            return GraspCallResponse(
                success=True,
                data=result,
                fallback=True,
                fallback_source="local_keyword_search",
                duration_ms=0,
            )
        
        try:
            return await self._circuit_breaker.call(
                _call_remote,
                fallback=_fallback_fn,
            )
        except CircuitBreakerOpen:
            result = self._fallback.dispatch_cognition(
                task_id, task_title, task_description, task_type, context, max_cognitions
            )
            return GraspCallResponse(
                success=True,
                data=result,
                fallback=True,
                fallback_source="local_keyword_search",
                duration_ms=0,
            )
    
    async def _call_remote_dispatch_cognition(
        self,
        task_id: str,
        task_title: str,
        task_description: str,
        task_type: str,
        context: Optional[Dict[str, Any]],
        max_cognitions: int
    ) -> GraspCallResponse:
        """远程调用认知抽取"""
        request_data = {
            "task": {
                "id": task_id,
                "title": task_title,
                "description": task_description,
                "type": task_type,
                "context": context or {}
            },
            "options": {
                "max_cognitions": max_cognitions,
                "include_sources": True
            }
        }
        
        try:
            response = await self._client.post(
                f"{self._base_url}/api/v1/grasp/dispatch-cognition",
                json=request_data,
                timeout=3.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return GraspCallResponse(
                    success=True,
                    data=data,
                    cache_hit=data.get("cache_hit", False),
                    duration_ms=response.elapsed.microseconds // 1000
                )
            elif response.status_code == 503:
                data = response.json()
                return GraspCallResponse(
                    success=True,
                    data=data.get("fallback_data", {"cognitions": [], "total": 0}),
                    cache_hit=False,
                    duration_ms=response.elapsed.microseconds // 1000,
                    error="Grasp service degraded",
                    fallback=True,
                    fallback_source="grasp_503",
                )
            else:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
        except (httpx.ConnectError, httpx.TimeoutException):
            raise
        except Exception:
            raise
    
    # === 认知反馈 ===
    
    async def send_cognitive_feedback(
        self,
        task_id: str,
        execution_result: Dict[str, Any],
        learnings: Dict[str, Any]
    ) -> bool:
        """认知回流 - 优先远程，失败时本地缓存"""
        try:
            response = await self._client.post(
                f"{self._base_url}/api/v1/grasp/feedback",
                json={
                    "task_id": task_id,
                    "execution_result": execution_result,
                    "learnings": learnings
                },
                timeout=10.0
            )
            return response.status_code == 202
        except Exception:
            # 降级到本地缓存
            return self._fallback.cognitive_feedback(
                task_id, execution_result, learnings
            )
    
    # === 执行监控 ===
    
    async def send_execution_monitoring(
        self,
        task_id: str,
        execution_state: Dict[str, Any],
        callbacks: Dict[str, str]
    ) -> bool:
        """执行监控 - 异步调用"""
        try:
            response = await self._client.post(
                f"{self._base_url}/api/v1/grasp/execution-monitoring",
                json={
                    "task_id": task_id,
                    "execution_state": execution_state,
                    "callbacks": callbacks
                },
                timeout=10.0
            )
            return response.status_code == 202
        except Exception:
            return False

# === 全局实例 ===

_grasp_client: Optional[GraspClient] = None

def get_grasp_client(base_url: Optional[str] = None) -> GraspClient:
    """
    获取全局 Grasp 客户端实例 (单例)
    
    :param base_url: 可选覆盖 Grasp 服务地址
    :return: GraspClient 实例
    """
    global _grasp_client
    if _grasp_client is None:
        _grasp_client = GraspClient(base_url=base_url)
    return _grasp_client

def reset_grasp_client():
    """重置全局 Grasp 客户端实例 (用于测试)"""
    global _grasp_client
    _grasp_client = None
