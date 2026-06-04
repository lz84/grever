"""
Reins Grasp 模块

提供与 Grasp 服务通信的客户端，支持:
- 熔断器 (Circuit Breaker)
- 本地降级引擎 (Fallback Engine)
- 优雅降级 (Graceful Degradation)
"""

from reins.common.grasp_client.caller import (
    GraspClient,
    GraspCallResponse,
    GraspCallRequest,
    GraspCapability,
    IGraspClient,
    get_grasp_client,
    reset_grasp_client,
)
from reins.common.grasp_client.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitState,
)
from reins.common.grasp_client.fallback import (
    GraspFallbackEngine,
    INTENT_TEMPLATES,
)

__all__ = [
    "GraspClient",
    "GraspCallResponse",
    "GraspCallRequest",
    "GraspCapability",
    "IGraspClient",
    "get_grasp_client",
    "reset_grasp_client",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerOpen",
    "CircuitState",
    "GraspFallbackEngine",
    "INTENT_TEMPLATES",
]
