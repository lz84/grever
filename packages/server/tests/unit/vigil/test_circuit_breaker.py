"""
P6-06 熔断器单元测试 (Circuit Breaker Unit Tests)

测试覆盖:
- 正常调用（CLOSED 状态）
- 连续失败触发熔断（CLOSED → OPEN）
- 冷却后自动恢复（OPEN → HALF_OPEN）
- 半开状态成功恢复（HALF_OPEN → CLOSED）
- 半开状态失败重新熔断（HALF_OPEN → OPEN）
- 降级函数调用
- 统计信息
- 手动重置和强制打开
"""

import pytest
import asyncio
import time

from reins.common.grasp_client.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitState,
)


class TestCircuitState:
    def test_states_exist(self):
        assert CircuitState.CLOSED == "closed"
        assert CircuitState.OPEN == "open"
        assert CircuitState.HALF_OPEN == "half_open"


class TestCircuitBreakerConfig:
    def test_defaults(self):
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 3
        assert config.recovery_timeout_ms == 30000
        assert config.success_threshold == 1


class TestCircuitBreakerOpen:
    def test_exception_message(self):
        exc = CircuitBreakerOpen(CircuitState.OPEN, 5000)
        assert "open" in str(exc).lower()
        assert exc.state == CircuitState.OPEN
        assert exc.remaining_ms == 5000


class TestCircuitBreakerBasic:
    @pytest.mark.asyncio
    async def test_initial_state(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_initial_stats(self):
        cb = CircuitBreaker()
        stats = cb.stats
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0
        assert stats["total_calls"] == 0

    @pytest.mark.asyncio
    async def test_successful_call_sync(self):
        cb = CircuitBreaker()
        result = await cb.call(lambda: "ok")
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_successful_call_async(self):
        cb = CircuitBreaker()
        async def async_func():
            return "async_ok"
        result = await cb.call(async_func)
        assert result == "async_ok"


class TestCircuitBreakerFailure:
    @pytest.mark.asyncio
    async def test_single_failure_stays_closed(self):
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))
        def fail():
            raise ValueError("error")
        with pytest.raises(ValueError):
            await cb.call(fail)
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_reaching_threshold_opens_circuit(self):
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))
        def fail():
            raise ValueError("error")
        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(fail)
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_uses_fallback(self):
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2))
        def fail():
            raise ValueError("error")
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(fail)
        assert cb.state == CircuitState.OPEN
        result = await cb.call(fail, fallback=lambda: "fallback")
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_open_circuit_raises_without_fallback(self):
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2))
        def fail():
            raise ValueError("error")
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(fail)
        assert cb.state == CircuitState.OPEN
        with pytest.raises(CircuitBreakerOpen):
            await cb.call(fail)


class TestCircuitBreakerRecovery:
    @pytest.mark.asyncio
    async def test_half_open_on_timeout(self):
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout_ms=100)
        cb = CircuitBreaker(config)
        def fail():
            raise ValueError("error")
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(fail)
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self):
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout_ms=100)
        cb = CircuitBreaker(config)
        def fail():
            raise ValueError("error")
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(fail)
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        result = await cb.call(lambda: "ok")
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self):
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout_ms=100)
        cb = CircuitBreaker(config)
        def fail():
            raise ValueError("error")
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(fail)
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        with pytest.raises(ValueError):
            await cb.call(fail)
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerManual:
    @pytest.mark.asyncio
    async def test_reset(self):
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2))
        def fail():
            raise ValueError("error")
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(fail)
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.stats["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_force_open(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        cb.force_open()
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerStats:
    @pytest.mark.asyncio
    async def test_stats_track_total_calls(self):
        cb = CircuitBreaker()
        await cb.call(lambda: "ok")
        await cb.call(lambda: "ok")
        assert cb.stats["total_calls"] == 2

    @pytest.mark.asyncio
    async def test_stats_track_fallbacks(self):
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        def fail():
            raise ValueError("error")
        with pytest.raises(ValueError):
            await cb.call(fail)
        assert cb.state == CircuitState.OPEN
        await cb.call(fail, fallback=lambda: "fb")
        assert cb.stats["total_fallbacks"] >= 1


class TestCircuitBreakerAsyncFallback:
    @pytest.mark.asyncio
    async def test_async_fallback(self):
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        async def fail():
            raise ValueError("error")
        with pytest.raises(ValueError):
            await cb.call(fail)
        cb.force_open()
        async def async_fallback():
            return "async_fallback"
        result = await cb.call(fail, fallback=async_fallback)
        assert result == "async_fallback"
