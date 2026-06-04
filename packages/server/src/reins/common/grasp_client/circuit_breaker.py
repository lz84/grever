"""
Grasp 服务熔断器 (Circuit Breaker)

状态机:
- CLOSED (闭合): 正常调用 Grasp 服务
- OPEN (断开): Grasp 不可用，快速失败，不调用
- HALF_OPEN (半开): 试探性调用，检测 Grasp 是否恢复

转换规则:
- CLOSED → OPEN: 连续失败次数达到阈值
- OPEN → HALF_OPEN: 冷却时间到达后
- HALF_OPEN → CLOSED: 试探调用成功
- HALF_OPEN → OPEN: 试探调用失败
"""

import time
import asyncio
from typing import Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass, field

class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 3        # 连续失败多少次后熔断
    recovery_timeout_ms: int = 30000  # 熔断后多久尝试恢复 (30秒)
    success_threshold: int = 1        # 半开状态下成功多少次后恢复

class CircuitBreakerOpen(Exception):
    """熔断器已打开，请求被拒绝"""
    def __init__(self, state: CircuitState, remaining_ms: int = 0):
        self.state = state
        self.remaining_ms = remaining_ms
        super().__init__(
            f"Circuit breaker is {state.value}, retry in {remaining_ms}ms"
        )

class CircuitBreaker:
    """
    熔断器实现
    
    用法:
        cb = CircuitBreaker()
        try:
            result = await cb.call(grasp_client.some_method, arg1, arg2)
        except CircuitBreakerOpen:
            # 使用降级方案
            fallback_result = local_fallback()
    """
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._opened_at: Optional[float] = None
        self._total_calls = 0
        self._total_failures = 0
        self._total_fallbacks = 0
    
    @property
    def state(self) -> CircuitState:
        """获取当前状态，考虑超时自动转换"""
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            elapsed_ms = (time.monotonic() - self._opened_at) * 1000
            if elapsed_ms >= self._config.recovery_timeout_ms:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
        return self._state
    
    @property
    def stats(self) -> dict:
        """获取熔断器统计"""
        return {
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "total_fallbacks": self._total_fallbacks,
            "failure_threshold": self._config.failure_threshold,
            "recovery_timeout_ms": self._config.recovery_timeout_ms,
        }
    
    async def call(
        self,
        func: Callable,
        *args,
        fallback: Optional[Callable] = None,
        fallback_args: tuple = (),
        **kwargs
    ) -> Any:
        """
        通过熔断器调用函数
        
        :param func: 要调用的函数 (异步或同步)
        :param fallback: 降级函数，当熔断器打开时调用
        :param fallback_args: 降级函数的参数
        :return: 调用结果
        """
        self._total_calls += 1
        current_state = self.state
        
        # 如果熔断器打开，直接使用降级方案
        if current_state == CircuitState.OPEN:
            self._total_fallbacks += 1
            remaining_ms = self._remaining_ms()
            if fallback:
                result = fallback(*fallback_args, **kwargs)
                if asyncio.iscoroutine(result):
                    return await result
                return result
            raise CircuitBreakerOpen(CircuitState.OPEN, remaining_ms)
        
        # 执行调用
        try:
            result = func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            
            # 调用成功
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            
            # 如果熔断器打开了，使用降级方案
            if self.state == CircuitState.OPEN:
                self._total_fallbacks += 1
                if fallback:
                    result = fallback(*fallback_args, **kwargs)
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
            
            raise
    
    def _on_success(self):
        """处理成功调用"""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._config.success_threshold:
                # 恢复到闭合状态
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                self._opened_at = None
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0
    
    def _on_failure(self):
        """处理失败调用"""
        self._total_failures += 1
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        
        if self._state == CircuitState.HALF_OPEN:
            # 半开状态下的失败，重新打开
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self._config.failure_threshold:
                # 达到失败阈值，打开熔断器
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
    
    def _remaining_ms(self) -> int:
        """计算到恢复还有多少毫秒"""
        if self._opened_at is None:
            return 0
        elapsed_ms = (time.monotonic() - self._opened_at) * 1000
        remaining = self._config.recovery_timeout_ms - elapsed_ms
        return max(0, int(remaining))
    
    def reset(self):
        """手动重置熔断器"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._opened_at = None
    
    def force_open(self):
        """手动打开熔断器"""
        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()
