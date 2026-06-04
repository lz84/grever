"""
Test Context Injector (Sprint 2)

测试范围：
- SP2-15: Agent 上下文注入服务
- SP2-16: 基于任务状态的动态上下文
- SP2-17: 上下文缓存和失效策略

验收标准：
- 上下文注入延迟 < 100ms（缓存命中）
- 缓存命中率 > 80%
- 上下文大小可配置

pytest-asyncio mode: auto
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# pytest-asyncio configuration
pytest_plugins = ('pytest_asyncio',)

from reins.core.context_injector import (
    ContextInjector, ContextQuery, TaskStatus, InjectionConfig,
    LRUCache, ContextTemplate, CONTEXT_TEMPLATES, GraspAdapter
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_grasp_service():
    """模拟 Grasp 服务"""
    service = Mock()
    service.retrieve = Mock(return_value=Mock(items=[]))
    service.list_cognitions = Mock(return_value=[])
    return service


@pytest.fixture
def injector(mock_grasp_service):
    """创建 ContextInjector 实例"""
    config = InjectionConfig(
        max_context_size=10000,
        max_cognitions=10,
        cache_max_size=50,
        cache_ttl_seconds=600,
    )
    return ContextInjector(
        max_cache_size=config.cache_max_size,
        default_ttl_seconds=config.cache_ttl_seconds,
        config=config,
    )


@pytest.fixture
def sample_task():
    """创建模拟任务对象"""
    task = Mock()
    task.id = "task-test-001"
    task.title = "实现用户认证模块"
    task.description = "开发基于 JWT 的用户认证系统，包括登录、注册、刷新令牌等功能"
    task.assigned_agent = "agent-coder-01"
    task.status = TaskStatus.TODO
    task.input_data = {}
    return task


# ============================================================================
# Tests: Context Template
# ============================================================================

class TestContextTemplate:
    """测试上下文模板"""
    
    def test_todo_template(self):
        """测试 TODO 状态模板"""
        template = CONTEXT_TEMPLATES[TaskStatus.TODO]
        assert template.title == "任务准备阶段"
        assert "目标" in template.instructions
        assert "任务目标与期望结果" in template.sections
    
    def test_in_progress_template(self):
        """测试 IN_PROGRESS 状态模板"""
        template = CONTEXT_TEMPLATES[TaskStatus.IN_PROGRESS]
        assert template.title == "任务执行阶段"
        assert "执行指南" in template.instructions
        assert "执行步骤和方法论" in template.sections
    
    def test_done_template(self):
        """测试 DONE 状态模板"""
        template = CONTEXT_TEMPLATES[TaskStatus.DONE]
        assert template.title == "任务完成阶段"
        assert "总结" in template.instructions
        assert "经验总结与教训" in template.sections


# ============================================================================
# Tests: LRUCache
# ============================================================================

class TestLRUCache:
    """测试 LRU 缓存"""
    
    @pytest.mark.asyncio
    async def test_basic_set_get(self):
        """测试基本设置和获取"""
        cache = LRUCache(max_size=10, default_ttl_seconds=300)
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """测试缓存未命中"""
        cache = LRUCache(max_size=10, default_ttl_seconds=300)
        result = await cache.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """测试 LRU 淘汰"""
        cache = LRUCache(max_size=3, default_ttl_seconds=300)
        
        # 添加 3 个条目
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # 访问 key1，使其成为最近使用
        await cache.get("key1")
        
        # 添加第 4 个条目，应该淘汰 key2（最久未使用）
        await cache.set("key4", "value4")
        
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") is None  # 被淘汰
        assert await cache.get("key3") == "value3"
        assert await cache.get("key4") == "value4"
    
    @pytest.mark.asyncio
    async def test_status_invalidation(self):
        """测试基于状态的失效"""
        cache = LRUCache(max_size=10, default_ttl_seconds=300)
        
        # 设置带状态的缓存
        await cache.set("task1:agent1:todo:v1", "value1", status="todo", cognition_version="v1")
        
        # 相同状态应该可以获取
        result = await cache.get("task1:agent1:todo:v1", status="todo", cognition_version="v1")
        assert result == "value1"
        
        # 不同状态应该失效
        result = await cache.get("task1:agent1:todo:v1", status="in_progress", cognition_version="v1")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cognition_version_invalidation(self):
        """测试基于认知版本的失效"""
        cache = LRUCache(max_size=10, default_ttl_seconds=300)
        
        # 设置带认知版本的缓存
        await cache.set("task1:agent1:todo:v1", "value1", status="todo", cognition_version="v1")
        
        # 相同版本应该可以获取
        result = await cache.get("task1:agent1:todo:v1", status="todo", cognition_version="v1")
        assert result == "value1"
        
        # 不同版本应该失效
        result = await cache.get("task1:agent1:todo:v1", status="todo", cognition_version="v2")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_stats(self):
        """测试统计信息"""
        cache = LRUCache(max_size=10, default_ttl_seconds=300)
        
        await cache.set("key1", "value1")
        await cache.get("key1")  # hit
        await cache.get("key2")  # miss
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5


# ============================================================================
# Tests: ContextQuery
# ============================================================================

class TestContextQuery:
    """测试上下文查询"""
    
    def test_query_to_query_string(self):
        """测试查询字符串生成"""
        query = ContextQuery(
            task_id="task-001",
            task_title="用户认证",
            task_description="开发认证系统",
            status=TaskStatus.TODO,
        )
        
        query_string = query.to_query_string()
        assert "用户认证" in query_string
        assert "开发认证系统" in query_string
        assert "任务目标" in query_string  # TODO 状态特有
    
    def test_query_to_cache_key(self):
        """测试缓存键生成"""
        query = ContextQuery(
            task_id="task-001",
            task_title="测试",
            agent_id="agent-01",
            status=TaskStatus.IN_PROGRESS,
        )
        
        cache_key = query.to_cache_key()
        assert "task-001" in cache_key
        assert "agent-01" in cache_key
        assert "in_progress" in cache_key


# ============================================================================
# Tests: GraspAdapter
# ============================================================================

class TestGraspAdapter:
    """测试 Grasp 适配器"""
    
    @pytest.mark.asyncio
    async def test_retrieve_empty(self, mock_grasp_service):
        """测试检索空结果"""
        adapter = GraspAdapter(service=mock_grasp_service)
        result = await adapter.retrieve(query="test query")
        assert result == []
    
    @pytest.mark.asyncio
    async def test_cognition_version(self, mock_grasp_service):
        """测试认知版本获取"""
        mock_grasp_service.list_cognitions.return_value = [1, 2, 3]
        adapter = GraspAdapter(service=mock_grasp_service)
        
        version = adapter.get_cognition_version()
        assert version == "3"


# ============================================================================
# Tests: ContextInjector
# ============================================================================

class TestContextInjector:
    """测试上下文注入器"""
    
    @pytest.mark.asyncio
    async def test_inject_for_task_todo(self, injector, sample_task):
        """测试 TODO 状态的任务注入"""
        prompt = await injector.inject_for_task(sample_task)
        
        assert sample_task.title in prompt
        assert "任务准备阶段" in prompt
        assert "任务目标" in prompt
    
    @pytest.mark.asyncio
    async def test_inject_for_task_in_progress(self, injector, sample_task):
        """测试 IN_PROGRESS 状态的任务注入"""
        sample_task.status = TaskStatus.IN_PROGRESS
        prompt = await injector.inject_for_task(sample_task)
        
        assert "任务执行阶段" in prompt
        assert "执行指南" in prompt
    
    @pytest.mark.asyncio
    async def test_inject_for_task_done(self, injector, sample_task):
        """测试 DONE 状态的任务注入"""
        sample_task.status = TaskStatus.DONE
        prompt = await injector.inject_for_task(sample_task)
        
        assert "任务完成阶段" in prompt
        assert "总结" in prompt
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, injector, sample_task):
        """测试缓存命中"""
        # 第一次注入（未命中）
        prompt1 = await injector.inject_for_task(sample_task)
        
        # 第二次注入（命中）
        prompt2 = await injector.inject_for_task(sample_task)
        
        # 两次结果应该相同
        assert prompt1 == prompt2
        
        # 检查统计
        stats = injector.get_stats()
        assert stats["cache_hits"] >= 1
    
    @pytest.mark.asyncio
    async def test_context_size_limit(self, injector, sample_task):
        """测试上下文大小限制"""
        # 配置最大大小
        injector.config.max_context_size = 500
        
        prompt = await injector.inject_for_task(sample_task)
        
        assert len(prompt) <= 500 + 200  # 允许截断标记
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_status_change(self, injector, sample_task):
        """测试任务状态变更时缓存失效"""
        # TODO 状态
        sample_task.status = TaskStatus.TODO
        prompt1 = await injector.inject_for_task(sample_task)
        
        # 变更为 IN_PROGRESS，应该失效缓存
        sample_task.status = TaskStatus.IN_PROGRESS
        await injector.invalidate_cache(sample_task.id, sample_task.status)
        
        prompt2 = await injector.inject_for_task(sample_task)
        
        # 两次内容应该不同（因为状态不同）
        assert "任务准备阶段" in prompt1
        assert "任务执行阶段" in prompt2
    
    @pytest.mark.asyncio
    async def test_batch_inject(self, injector, sample_task):
        """测试批量注入"""
        # 创建多个任务
        tasks = [sample_task for _ in range(3)]
        for i, task in enumerate(tasks):
            task.id = f"task-{i}"
        
        results = await injector.batch_inject(tasks)
        
        assert len(results) == 3
        assert all(task.id in results for task in tasks)
    
    @pytest.mark.asyncio
    async def test_stats(self, injector, sample_task):
        """测试统计信息"""
        await injector.inject_for_task(sample_task)
        await injector.inject_for_task(sample_task)
        
        stats = injector.get_stats()
        
        assert stats["total_injections"] == 2
        assert "cache" in stats
        assert "latency_check" in stats
        assert "hit_rate_check" in stats


# ============================================================================
# Tests: Performance and Acceptance Criteria
# ============================================================================

class TestAcceptanceCriteria:
    """测试验收标准"""
    
    @pytest.mark.asyncio
    async def test_latency_under_100ms_with_cache(self, injector, sample_task):
        """
        验收标准：上下文注入延迟 < 100ms（缓存命中）
        """
        # 第一次注入（未命中）
        await injector.inject_for_task(sample_task)
        
        # 第二次注入（命中），测量时间
        start = asyncio.get_event_loop().time()
        await injector.inject_for_task(sample_task)
        elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000
        
        assert elapsed_ms < 100, f"延迟 {elapsed_ms:.2f}ms 超过 100ms"
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate_over_80(self, injector, sample_task):
        """
        验收标准：缓存命中率 > 80%
        """
        # 进行多次注入
        num_injections = 100
        for _ in range(num_injections):
            await injector.inject_for_task(sample_task)
        
        stats = injector.get_stats()
        hit_rate = stats["cache"]["hit_rate"]
        
        assert hit_rate > 0.8, f"缓存命中率 {hit_rate:.2%} 低于 80%"
    
    @pytest.mark.asyncio
    async def test_context_size_configurable(self, injector, sample_task):
        """
        验收标准：上下文大小可配置
        """
        # 配置不同的大小限制
        for size in [1000, 5000, 10000]:
            injector.config.max_context_size = size
            prompt = await injector.inject_for_task(sample_task)
            assert len(prompt) <= size + 200


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Run with pytest-asyncio mode=auto
    pytest.main([__file__, "-v", "-s", "--asyncio-mode=auto"])
