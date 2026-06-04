"""
Grasp 优雅降级机制测试

测试内容:
1. CircuitBreaker 状态转换
2. FallbackEngine 各能力降级
3. GraspClient 熔断+降级集成
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock

# 导入被测模块
from reins.grasp.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpen,
    CircuitState,
)
from reins.grasp.fallback import GraspFallbackEngine, INTENT_TEMPLATES
from reins.grasp.caller import (
    GraspClient,
    GraspCallResponse,
    get_grasp_client,
    reset_grasp_client,
)


# ============================================================
# CircuitBreaker 测试
# ============================================================

class TestCircuitBreaker:
    """熔断器状态机测试"""
    
    def test_initial_state_closed(self):
        """初始状态为 CLOSED"""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
    
    def test_opens_after_failures(self):
        """连续失败达到阈值后打开"""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout_ms=1000)
        cb = CircuitBreaker(config)
        
        # 第一次失败
        async def failing_func():
            raise ConnectionError("test")
        
        async def run_test():
            try:
                await cb.call(failing_func)
            except ConnectionError:
                pass
            assert cb.state == CircuitState.CLOSED  # 还未达到阈值
            
            # 第二次失败 → 打开
            try:
                await cb.call(failing_func)
            except ConnectionError:
                pass
            assert cb.state == CircuitState.OPEN
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    def test_rejects_when_open(self):
        """打开状态下拒绝调用"""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_ms=10000)
        cb = CircuitBreaker(config)
        
        async def run_test():
            # 触发打开
            async def failing():
                raise ConnectionError()
            try:
                await cb.call(failing)
            except:
                pass
            
            assert cb.state == CircuitState.OPEN
            
            # 调用应该被拒绝
            async def success():
                return "ok"
            
            try:
                await cb.call(success)
                pytest.fail("Should have raised CircuitBreakerOpen")
            except CircuitBreakerOpen as e:
                assert e.state == CircuitState.OPEN
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    def test_recovery_after_timeout(self):
        """超时后自动转为半开状态"""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_ms=100)
        cb = CircuitBreaker(config)
        
        async def run_test():
            async def failing():
                raise ConnectionError()
            try:
                await cb.call(failing)
            except:
                pass
            
            assert cb.state == CircuitState.OPEN
            
            # 等待恢复超时
            await asyncio.sleep(0.15)
            
            assert cb.state == CircuitState.HALF_OPEN
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    def test_half_open_to_closed_on_success(self):
        """半开状态下成功后恢复闭合"""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_ms=100)
        cb = CircuitBreaker(config)
        
        async def run_test():
            async def failing():
                raise ConnectionError()
            try:
                await cb.call(failing)
            except:
                pass
            
            await asyncio.sleep(0.15)
            assert cb.state == CircuitState.HALF_OPEN
            
            # 成功调用
            result = await cb.call(lambda: "ok")
            assert result == "ok"
            assert cb.state == CircuitState.CLOSED
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    def test_fallback_when_open(self):
        """打开时使用降级方案"""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_ms=10000)
        cb = CircuitBreaker(config)
        
        async def run_test():
            async def failing():
                raise ConnectionError()
            try:
                await cb.call(failing)
            except:
                pass
            
            assert cb.state == CircuitState.OPEN
            
            # 调用带降级
            result = await cb.call(
                lambda: "remote",
                fallback=lambda: "fallback",
            )
            assert result == "fallback"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    def test_stats(self):
        """统计信息正确"""
        cb = CircuitBreaker()
        stats = cb.stats
        
        assert "state" in stats
        assert "failure_count" in stats
        assert "total_calls" in stats
        assert stats["total_calls"] == 0
    
    def test_manual_reset(self):
        """手动重置"""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker(config)
        
        async def run_test():
            async def failing():
                raise ConnectionError()
            try:
                await cb.call(failing)
            except:
                pass
            
            assert cb.state == CircuitState.OPEN
            cb.reset()
            assert cb.state == CircuitState.CLOSED
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    def test_force_open(self):
        """手动打开"""
        cb = CircuitBreaker()
        cb.force_open()
        assert cb.state == CircuitState.OPEN


# ============================================================
# FallbackEngine 测试
# ============================================================

class TestFallbackEngine:
    """本地降级引擎测试"""
    
    def setup_method(self):
        self.engine = GraspFallbackEngine()
    
    def test_intent_understanding_development(self):
        """开发类意图识别"""
        result = self.engine.intent_understanding(
            "开发一个用户管理系统"
        )
        assert result["intent"]["type"] == "development"
        assert result["fallback"] is True
    
    def test_intent_understanding_design(self):
        """设计类意图识别"""
        result = self.engine.intent_understanding(
            "设计系统架构方案"
        )
        assert result["intent"]["type"] == "design"
    
    def test_intent_understanding_research(self):
        """调研类意图识别"""
        result = self.engine.intent_understanding(
            "调研技术方案对比"
        )
        assert result["intent"]["type"] == "research"
    
    def test_intent_understanding_troubleshoot(self):
        """排障类意图识别"""
        result = self.engine.intent_understanding(
            "修复登录页面的 bug"
        )
        assert result["intent"]["type"] == "troubleshoot"
    
    def test_intent_understanding_general(self):
        """通用意图识别（无匹配模板）"""
        result = self.engine.intent_understanding(
            "随便做点什么"
        )
        assert result["intent"]["type"] == "general"
        assert "suggested_tasks" in result
    
    def test_agent_matching(self):
        """智能体匹配"""
        agents = [
            {"id": "agent1", "name": "Coder", "capabilities": ["coding", "testing"]},
            {"id": "agent2", "name": "Designer", "capabilities": ["design", "review"]},
            {"id": "agent3", "name": "DevOps", "capabilities": ["devops", "deployment"]},
        ]
        
        result = self.engine.agent_matching(
            task_requirements={"required_capabilities": ["coding", "testing"]},
            available_agents=agents,
        )
        
        assert result["fallback"] is True
        assert len(result["matched_agents"]) > 0
        assert result["matched_agents"][0]["agent_id"] == "agent1"
    
    def test_dispatch_cognition(self):
        """认知抽取降级"""
        result = self.engine.dispatch_cognition(
            task_id="task-1",
            task_title="开发 API 接口",
            task_description="实现 RESTful API",
            task_type="development",
            max_cognitions=3,
        )
        
        assert result["fallback"] is True
        assert "cognitions" in result
        assert "keywords_used" in result
    
    def test_cognitive_feedback(self):
        """认知反馈本地缓存"""
        success = self.engine.cognitive_feedback(
            task_id="task-1",
            execution_result={"status": "done"},
            learnings={"lesson": "test early"},
        )
        assert success is True
    
    def test_reload(self):
        """重新加载知识库"""
        self.engine.reload()
        # 不应抛出异常
        assert True
    
    def test_extract_keywords(self):
        """关键词提取"""
        keywords = GraspFallbackEngine._extract_keywords(
            "开发一个用户管理系统"
        )
        # 过滤掉停用词后应该有多个关键词
        assert len(keywords) > 0
        # 验证关键词不包含停用词
        assert "的" not in keywords
        assert "了" not in keywords
        # 英文关键词测试
        en_keywords = GraspFallbackEngine._extract_keywords("develop a user management system")
        assert "develop" in en_keywords
        assert "user" in en_keywords
        assert "management" in en_keywords
        assert "system" in en_keywords


# ============================================================
# Integration Tests (mocked remote)
# ============================================================

class TestGraspClientIntegration:
    """GraspClient 集成测试（模拟远程调用）"""
    
    def setup_method(self):
        reset_grasp_client()
    
    def teardown_method(self):
        reset_grasp_client()
    
    def test_fallback_when_circuit_open(self):
        """熔断器打开后使用降级"""
        async def run_test():
            # 使用极低的失败阈值，确保第一次失败就打开熔断器
            client = GraspClient(
                base_url="http://nonexistent:9999",
                circuit_breaker_config=CircuitBreakerConfig(
                    failure_threshold=1,
                    recovery_timeout_ms=10000,  # 很长的恢复时间
                )
            )
            
            # 第一次调用 → 失败 → 打开熔断器
            try:
                await client.call_intent_understanding("测试1", {})
            except RuntimeError:
                pass  # 第一次失败正常
            
            # 第二次调用 → 熔断器打开 → 降级
            response = await client.call_intent_understanding(
                user_goal="开发一个系统",
                context={}
            )
            
            # 应该成功（使用降级）
            assert response.success is True
            assert response.fallback is True
            assert response.fallback_source == "local_template_engine"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    def test_circuit_breaker_opens_after_failures(self):
        """多次失败后熔断器打开"""
        async def run_test():
            client = GraspClient(
                base_url="http://nonexistent:9999",
                circuit_breaker_config=CircuitBreakerConfig(
                    failure_threshold=1,
                    recovery_timeout_ms=10000,
                )
            )
            
            # 第一次调用（失败 → 打开）
            try:
                await client.call_intent_understanding("测试1", {})
            except RuntimeError:
                pass
            
            stats = client.get_circuit_breaker_stats()
            assert stats["state"] == "open"
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    def test_response_has_fallback_flag(self):
        """降级响应带有 fallback 标记"""
        async def run_test():
            client = GraspClient(
                base_url="http://nonexistent:9999",
                circuit_breaker_config=CircuitBreakerConfig(
                    failure_threshold=1,
                    recovery_timeout_ms=10000,
                )
            )
            
            # 第一次失败
            try:
                await client.call_intent_understanding("测试1", {})
            except RuntimeError:
                pass
            
            # 第二次使用降级
            response = await client.call_intent_understanding(
                user_goal="开发一个系统",
                context={}
            )
            
            assert response.fallback is True
            assert response.fallback_source is not None
            assert response.data is not None
        
        asyncio.get_event_loop().run_until_complete(run_test())
    
    def test_fallback_response_data_structure(self):
        """降级响应数据结构完整"""
        async def run_test():
            client = GraspClient(
                base_url="http://nonexistent:9999",
                circuit_breaker_config=CircuitBreakerConfig(
                    failure_threshold=1,
                    recovery_timeout_ms=10000,
                )
            )
            
            # 第一次失败
            try:
                await client.call_intent_understanding("测试1", {})
            except RuntimeError:
                pass
            
            # 第二次使用降级
            response = await client.call_intent_understanding(
                user_goal="开发一个系统",
                context={}
            )
            
            data = response.data
            assert "intent" in data
            assert "suggested_tasks" in data
            assert data["intent"]["type"] == "development"
        
        asyncio.get_event_loop().run_until_complete(run_test())


# ============================================================
# Test Intent Templates
# ============================================================

class TestIntentTemplates:
    """意图模板完整性测试"""
    
    def test_templates_cover_all_types(self):
        """模板覆盖所有意图类型"""
        types = {t["intent"] for t in INTENT_TEMPLATES}
        expected = {
            "development", "design", "research",
            "troubleshoot", "deployment", "optimization",
            "testing", "documentation",
        }
        assert types == expected
    
    def test_all_templates_have_tasks(self):
        """所有模板都有建议任务"""
        for t in INTENT_TEMPLATES:
            assert "suggested_tasks" in t
            assert len(t["suggested_tasks"]) > 0
    
    def test_all_templates_have_confidence(self):
        """所有模板都有置信度"""
        for t in INTENT_TEMPLATES:
            assert "confidence" in t
            assert 0 < t["confidence"] <= 1.0
