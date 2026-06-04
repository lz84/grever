"""
Tests for Grasp Circuit Breaker and Fallback
P6-06 Grasp Graceful Degradation
"""
import pytest
import asyncio
import time
from typing import Any
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


class TestCircuitBreaker:
    """Test Circuit Breaker states and transitions"""
    
    def test_initial_state_is_closed(self):
        """Test that circuit breaker starts in CLOSED state"""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
    
    def test_stats_initial_values(self):
        """Test initial stats are correct"""
        cb = CircuitBreaker()
        stats = cb.stats
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0
        assert stats["success_count"] == 0
        assert stats["total_calls"] == 0
        assert stats["total_failures"] == 0
        assert stats["total_fallbacks"] == 0
    
    def test_call_success_in_closed_state(self):
        """Test successful call in closed state"""
        cb = CircuitBreaker()
        
        async def success_func():
            return "success"
        
        result = asyncio.run(cb.call(success_func))
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.stats["total_calls"] == 1
    
    def test_call_failure_transitions_to_open(self):
        """Test that failures transition to OPEN state"""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(config=config)
        
        async def fail_func():
            raise Exception("Intentional failure")
        
        # First failure
        with pytest.raises(Exception):
            asyncio.run(cb.call(fail_func))
        
        # Second failure
        with pytest.raises(Exception):
            asyncio.run(cb.call(fail_func))
        
        # Third failure - should open
        with pytest.raises(Exception):
            asyncio.run(cb.call(fail_func))
        
        assert cb.state == CircuitState.OPEN
    
    def test_open_circuitUsesFallback(self):
        """Test that open circuit uses fallback function"""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker(config=config)
        
        async def fail_func():
            raise Exception("Failure")
        
        def fallback():
            return "fallback_result"
        
        # Trigger circuit open
        for _ in range(2):
            with pytest.raises(Exception):
                asyncio.run(cb.call(fail_func))
        
        # Now call with fallback
        result = asyncio.run(cb.call(fail_func, fallback=fallback))
        assert result == "fallback_result"
        # Fallback was used twice (second failure + open state)
        assert cb.stats["total_fallbacks"] >= 1
    
    def test_open_circuitRaisesUnlessFallback(self):
        """Test that open circuit raises CircuitBreakerOpen if no fallback"""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker(config=config)
        
        async def fail_func():
            raise Exception("Failure")
        
        # Trigger circuit open
        with pytest.raises(Exception):
            asyncio.run(cb.call(fail_func))
        
        # Now should raise CircuitBreakerOpen
        with pytest.raises(CircuitBreakerOpen) as exc_info:
            asyncio.run(cb.call(fail_func))
        
        assert exc_info.value.state == CircuitState.OPEN
    
    def test_halfOpen_transition_after_timeout(self):
        """Test transition from OPEN to HALF_OPEN after timeout"""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout_ms=100
        )
        cb = CircuitBreaker(config=config)
        
        async def fail_func():
            raise Exception("Failure")
        
        # Trigger open
        with pytest.raises(Exception):
            asyncio.run(cb.call(fail_func))
        
        assert cb.state == CircuitState.OPEN
        
        # Force state transition (simulating time passing)
        cb._opened_at = time.monotonic() - 0.2  # Pretend time passed
        
        # Should be half_open now
        assert cb.state == CircuitState.HALF_OPEN
    
    def test_halfOpen_success_transitions_to_closed(self):
        """Test HALF_OPEN -> CLOSED on success"""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout_ms=100,
            success_threshold=1
        )
        cb = CircuitBreaker(config=config)
        
        async def fail_func():
            raise Exception("Failure")
        
        async def success_func():
            return "success"
        
        # Trigger open
        with pytest.raises(Exception):
            asyncio.run(cb.call(fail_func))
        
        # Force half_open state
        cb._opened_at = time.monotonic() - 0.2
        
        # Success in half_open should close
        result = asyncio.run(cb.call(success_func))
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
    
    def test_halfOpen_failure_transitions_back_to_open(self):
        """Test HALF_OPEN -> OPEN on failure"""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout_ms=100,
            success_threshold=1
        )
        cb = CircuitBreaker(config=config)
        
        async def fail_func():
            raise Exception("Failure")
        
        # Trigger open
        with pytest.raises(Exception):
            asyncio.run(cb.call(fail_func))
        
        # Wait for half_open
        asyncio.sleep(0.2)
        
        # Failure in half_open should re-open
        with pytest.raises(Exception):
            asyncio.run(cb.call(fail_func))
        
        assert cb.state == CircuitState.OPEN
    
    def test_reset_manually(self):
        """Test manual reset"""
        cb = CircuitBreaker()
        
        # Force open
        cb.force_open()
        assert cb.state == CircuitState.OPEN
        
        # Reset
        cb.reset()
        assert cb.state == CircuitState.CLOSED
    
    def test_force_open(self):
        """Test force open"""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        
        cb.force_open()
        assert cb.state == CircuitState.OPEN


class TestFallbackEngine:
    """Test Grasp Fallback Engine"""
    
    def test_intent_understanding_basic(self):
        """Test basic intent understanding"""
        engine = GraspFallbackEngine()
        
        result = engine.intent_understanding("开发一个新系统")
        
        assert "intent" in result
        assert result["fallback"] is True
        assert result["intent"]["type"] == "development"
        assert result["intent"]["domain"] == "engineering"
    
    def test_intent_understanding_design(self):
        """Test design intent detection"""
        engine = GraspFallbackEngine()
        
        result = engine.intent_understanding("设计一个新架构")
        
        assert result["intent"]["type"] == "design"
        assert result["intent"]["domain"] == "architecture"
    
    def test_intent_understanding_research(self):
        """Test research intent detection"""
        engine = GraspFallbackEngine()
        
        result = engine.intent_understanding("调研新技术方案")
        
        assert result["intent"]["type"] == "research"
        assert result["intent"]["domain"] == "research"
    
    def test_intent_understanding_troubleshoot(self):
        """Test troubleshooting intent detection"""
        engine = GraspFallbackEngine()
        
        result = engine.intent_understanding("修复一个bug")
        
        assert result["intent"]["type"] == "troubleshoot"
        assert result["intent"]["domain"] == "maintenance"
    
    def test_intent_understanding_no_match(self):
        """Test default when no template matches"""
        engine = GraspFallbackEngine()
        
        result = engine.intent_understanding("随便做点什么")
        
        assert result["intent"]["type"] == "general"
        assert result["fallback"] is True
    
    def test_agent_matching_basic(self):
        """Test basic agent matching"""
        engine = GraspFallbackEngine()
        
        available_agents = [
            {"id": "agent-1", "name": "Dev Agent", "capabilities": ["coding", "testing"]},
            {"id": "agent-2", "name": "Design Agent", "capabilities": ["design", "architecture"]},
        ]
        
        task_requirements = {
            "required_capabilities": ["coding"],
        }
        
        result = engine.agent_matching(task_requirements, available_agents)
        
        assert result["fallback"] is True
        assert len(result["matched_agents"]) > 0
        # The best match should be the first one due to sorting
        assert result["best_match"]["agent"].get("id") == "agent-1"
    
    def test_agent_matching_no_requirements(self):
        """Test agent matching with no requirements"""
        engine = GraspFallbackEngine()
        
        available_agents = [
            {"id": "agent-1", "name": "Agent 1", "capabilities": ["coding", "testing"]},
        ]
        
        task_requirements = {}
        
        result = engine.agent_matching(task_requirements, available_agents)
        
        assert result["matched_agents"][0]["agent_id"] == "agent-1"
    
    def test_dispatch_cognition_basic(self):
        """Test cognition dispatch"""
        engine = GraspFallbackEngine()
        
        result = engine.dispatch_cognition(
            task_id="task-001",
            task_title="开发功能",
            task_description="实现新功能",
            task_type="coding"
        )
        
        assert result["fallback"] is True
        assert "cognitions" in result
        assert "source" in result
    
    def test_cognitive_feedback(self):
        """Test cognitive feedback recording"""
        engine = GraspFallbackEngine()
        
        result = engine.cognitive_feedback(
            task_id="task-001",
            execution_result={"status": "success"},
            learnings={"key": "value"}
        )
        
        assert result is True


class TestFallbackTemplates:
    """Test intent templates"""
    
    def test_intent_templates_exist(self):
        """Test that intent templates are defined"""
        assert len(INTENT_TEMPLATES) > 0
        
        template_types = [t["intent"] for t in INTENT_TEMPLATES]
        assert "development" in template_types
        assert "design" in template_types
        assert "research" in template_types
        assert "troubleshoot" in template_types
    
    def test_template_patterns_compile(self):
        """Test that all template patterns are valid regex"""
        import re
        
        for template in INTENT_TEMPLATES:
            try:
                re.compile(template["pattern"])
            except re.error as e:
                pytest.fail(f"Invalid regex pattern in template {template['intent']}: {e}")


class TestIntegration:
    """Integration tests for Grasp degradation"""
    
    def test_full_degradation_workflow(self):
        """Test full degradation: open circuit -> use fallback"""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout_ms=100,
            success_threshold=1
        )
        cb = CircuitBreaker(config=config)
        engine = GraspFallbackEngine()
        
        # Simulate Grasp service failure
        async def grasp_service_call():
            raise ConnectionError("Grasp service unavailable")
        
        def degrade():
            # Use fallback when primary fails
            return engine.intent_understanding("开发一个新功能")
        
        # First call opens circuit
        with pytest.raises(ConnectionError):
            asyncio.run(cb.call(grasp_service_call))
        
        # Second call uses fallback (circuit is open)
        result = asyncio.run(cb.call(grasp_service_call, fallback=degrade))
        
        assert result["fallback"] is True
        assert "intent" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
