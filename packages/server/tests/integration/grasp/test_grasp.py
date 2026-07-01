"""
Grasp Backend 单元测试
测试 inject/retrieve/update/get_cognition 功能
测试 memory 模式下的持久化行为
测试置信度过滤、类型过滤、标签过滤
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest
from grasp.common.models import (
    CognitionInput, CognitionUpdate, Cognition,
    CognitionType, CognitionStatus, SourceInfo
)
from grasp.facade.service import GraspFacade
from shared.common.exceptions import GreverException


class TestGraspInject(unittest.TestCase):
    """测试 inject 功能"""

    def setUp(self):
        self.service = GraspFacade(storage_backend="memory")

    def test_inject_fact_basic(self):
        """注入基础 FACT 认知"""
        source = SourceInfo(agent_id="agent-1", task_id="task-1", channel="test")
        cognition_input = CognitionInput(
            type=CognitionType.FACT,
            content="Python 是一种高级编程语言",
            source=source,
            tags=["python", "编程语言"],
            confidence=0.9,
        )
        result = self.service.inject(cognition_input)

        self.assertIsNotNone(result.cognition_id)
        self.assertTrue(result.cognition_id.startswith("cog-"))
        self.assertIn(result.status, [CognitionStatus.PUBLISHED, CognitionStatus.PENDING_REVIEW])

    def test_inject_multiple_cognitions(self):
        """注入多条认知"""
        source = SourceInfo(agent_id="agent-1", task_id="task-1", channel="test")

        cog1 = CognitionInput(
            type=CognitionType.FACT,
            content="水在0度以下会结冰这是一个物理常识",
            source=source,
            tags=["物理", "水"],
            confidence=0.95,
        )
        cog2 = CognitionInput(
            type=CognitionType.PATTERN,
            content="递归调用需要终止条件才能正确返回",
            source=source,
            tags=["编程", "递归"],
            confidence=0.85,
        )
        cog3 = CognitionInput(
            type=CognitionType.LESSON,
            content="测试驱动开发可以提高代码质量和可靠性",
            source=source,
            tags=["TDD", "软件工程"],
            confidence=0.88,
        )

        r1 = self.service.inject(cog1)
        r2 = self.service.inject(cog2)
        r3 = self.service.inject(cog3)

        self.assertNotEqual(r1.cognition_id, r2.cognition_id)
        self.assertNotEqual(r2.cognition_id, r3.cognition_id)

        stored1 = self.service.get_cognition(r1.cognition_id)
        stored2 = self.service.get_cognition(r2.cognition_id)
        stored3 = self.service.get_cognition(r3.cognition_id)

        self.assertIsNotNone(stored1)
        self.assertIsNotNone(stored2)
        self.assertIsNotNone(stored3)

        self.assertEqual(stored1.type, CognitionType.FACT)
        self.assertEqual(stored2.type, CognitionType.PATTERN)
        self.assertEqual(stored3.type, CognitionType.LESSON)

    def test_inject_empty_content_raises(self):
        """空内容应该抛出异常"""
        source = SourceInfo(agent_id="agent-1", task_id="task-1", channel="test")
        cognition_input = CognitionInput(
            type=CognitionType.FACT,
            content="",
            source=source,
        )
        with self.assertRaises(GreverException) as ctx:
            self.service.inject(cognition_input)
        self.assertIn(ctx.exception.args[0].upper() if ctx.exception.args else "", ["GRASP_INVALID_CONTENT", "INVALID_CONTENT", ""])

    def test_inject_poison_content_raises(self):
        """危险内容应该被检测并拒绝"""
        source = SourceInfo(agent_id="agent-1", task_id="task-1", channel="test")
        cognition_input = CognitionInput(
            type=CognitionType.FACT,
            content="<script>alert('xss')</script>",
            source=source,
        )
        with self.assertRaises(GreverException) as ctx:
            self.service.inject(cognition_input)

    def test_inject_code_injection_raises(self):
        """代码注入应该被检测并拒绝"""
        source = SourceInfo(agent_id="agent-1", task_id="task-1", channel="test")
        cognition_input = CognitionInput(
            type=CognitionType.FACT,
            content="execute(system('ls'))",
            source=source,
        )
        with self.assertRaises(GreverException) as ctx:
            self.service.inject(cognition_input)

    def test_inject_low_confidence_pending_review(self):
        """极低置信度内容应该进入待审核状态"""
        source = SourceInfo(agent_id="agent-1", task_id="task-1", channel="test")
        cognition_input = CognitionInput(
            type=CognitionType.FACT,
            content="xyz",
            source=source,
            confidence=0.01,
        )
        result = self.service.inject(cognition_input)
        self.assertEqual(result.status, CognitionStatus.PENDING_REVIEW)

    def test_inject_short_content_pending_review(self):
        """过短内容应该进入待审核状态"""
        source = SourceInfo(agent_id="agent-1", task_id="task-1", channel="test")
        cognition_input = CognitionInput(
            type=CognitionType.FACT,
            content="a",
            source=source,
            confidence=0.05,
        )
        result = self.service.inject(cognition_input)
        self.assertEqual(result.status, CognitionStatus.PENDING_REVIEW)


class TestGraspRetrieve(unittest.TestCase):
    """测试 retrieve 功能"""

    def setUp(self):
        self.service = GraspFacade(storage_backend="memory")
        source = SourceInfo(agent_id="agent-1", task_id="task-1", channel="test")

        self.cog1 = self.service.inject(CognitionInput(
            type=CognitionType.FACT,
            content="Python 是一种高级编程语言，支持多种编程范式和编程思想",
            source=source,
            tags=["python", "编程"],
            confidence=0.9,
        ))
        self.cog2 = self.service.inject(CognitionInput(
            type=CognitionType.FACT,
            content="JavaScript 用于 Web 前端开发，也支持服务器端编程",
            source=source,
            tags=["javascript", "web"],
            confidence=0.85,
        ))
        self.cog3 = self.service.inject(CognitionInput(
            type=CognitionType.PATTERN,
            content="测试驱动开发先写测试再编程实现可以提高代码质量",
            source=source,
            tags=["TDD", "测试"],
            confidence=0.88,
        ))
        self.cog4 = self.service.inject(CognitionInput(
            type=CognitionType.FACT,
            content="Go 语言以其高效的并发支持著称，广泛用于服务器编程",
            source=source,
            tags=["go", "并发"],
            confidence=0.92,
        ))

    def test_retrieve_all(self):
        """检索多个匹配的结果"""
        result = self.service.retrieve("编程")
        self.assertGreaterEqual(result.total, 3,
            f"Expected at least 3 results for '编程', got {result.total}")

    def test_retrieve_by_type_filter(self):
        """按类型过滤检索"""
        result = self.service.retrieve(
            "编程",
            type=[CognitionType.FACT]
        )
        for item in result.items:
            self.assertEqual(item.type, CognitionType.FACT)

    def test_retrieve_by_tags_filter(self):
        """按标签过滤检索（AND 匹配）"""
        result = self.service.retrieve(
            "测试",
            tags=["TDD"]
        )
        for item in result.items:
            self.assertIn("TDD", item.tags)

    def test_retrieve_by_min_confidence(self):
        """按最低置信度过滤"""
        result = self.service.retrieve(
            "编程",
            min_confidence=0.9
        )
        for item in result.items:
            self.assertGreaterEqual(item.confidence, 0.9)

    def test_retrieve_pagination(self):
        """分页检索"""
        result = self.service.retrieve(
            "编程",
            limit=2,
            offset=0
        )
        self.assertLessEqual(len(result.items), 2)
        if result.total > 2:
            self.assertTrue(result.has_more)

    def test_retrieve_no_match(self):
        """无匹配结果"""
        result = self.service.retrieve("完全不存在的关键词 xyz123 abc")
        self.assertEqual(result.total, 0)
        self.assertEqual(len(result.items), 0)

    def test_retrieve_combined_filters(self):
        """组合过滤"""
        result = self.service.retrieve(
            "编程",
            type=[CognitionType.FACT],
            min_confidence=0.85,
            limit=10
        )
        for item in result.items:
            self.assertEqual(item.type, CognitionType.FACT)
            self.assertGreaterEqual(item.confidence, 0.85)


class TestGraspUpdate(unittest.TestCase):
    """测试 update 功能"""

    def setUp(self):
        self.service = GraspFacade(storage_backend="memory")
        source = SourceInfo(agent_id="agent-1", task_id="task-1", channel="test")
        self.cognition_input = CognitionInput(
            type=CognitionType.FACT,
            content="Python 是一种编程语言",
            source=source,
            tags=["python"],
            confidence=0.8,
        )
        self.result = self.service.inject(self.cognition_input)
        self.cog_id = self.result.cognition_id

    def test_update_content(self):
        """更新认知内容"""
        update = CognitionUpdate(content="Python 是一种高级编程语言")
        result = self.service.update(self.cog_id, update)

        self.assertEqual(result.cognition_id, self.cog_id)
        stored = self.service.get_cognition(self.cog_id)
        self.assertEqual(stored.content, "Python 是一种高级编程语言")

    def test_update_tags(self):
        """更新认知标签"""
        update = CognitionUpdate(tags=["python", "编程语言", "高级"])
        result = self.service.update(self.cog_id, update)

        stored = self.service.get_cognition(self.cog_id)
        self.assertIn("python", stored.tags)
        self.assertIn("编程语言", stored.tags)
        self.assertIn("高级", stored.tags)

    def test_update_confidence(self):
        """更新置信度"""
        update = CognitionUpdate(confidence=0.95)
        result = self.service.update(self.cog_id, update)

        stored = self.service.get_cognition(self.cog_id)
        self.assertEqual(stored.confidence, 0.95)

    def test_update_metadata(self):
        """更新元数据"""
        update = CognitionUpdate(metadata={"key": "value", "score": 100})
        result = self.service.update(self.cog_id, update)

        stored = self.service.get_cognition(self.cog_id)
        self.assertEqual(stored.metadata.get("key"), "value")
        self.assertEqual(stored.metadata.get("score"), 100)

    def test_update_nonexistent_raises(self):
        """更新不存在的认知应抛出异常"""
        update = CognitionUpdate(content="新内容")
        with self.assertRaises(GreverException) as ctx:
            self.service.update("non-existent-id", update)

    def test_update_poison_content_raises(self):
        """更新危险内容应被拒绝"""
        update = CognitionUpdate(content="<script>alert(1)</script>")
        with self.assertRaises(GreverException) as ctx:
            self.service.update(self.cog_id, update)


class TestGraspGetCognition(unittest.TestCase):
    """测试 get_cognition 功能"""

    def setUp(self):
        self.service = GraspFacade(storage_backend="memory")
        source = SourceInfo(agent_id="agent-1", task_id="task-1", channel="test")
        self.cognition_input = CognitionInput(
            type=CognitionType.FACT,
            content="测试内容用于获取方法",
            source=source,
            tags=["测试"],
            confidence=0.9,
        )
        self.result = self.service.inject(self.cognition_input)

    def test_get_cognition_exists(self):
        """获取存在的认知"""
        cog = self.service.get_cognition(self.result.cognition_id)
        self.assertIsNotNone(cog)
        self.assertEqual(cog.cognition_id, self.result.cognition_id)
        self.assertEqual(cog.content, "测试内容用于获取方法")

    def test_get_cognition_not_exists(self):
        """获取不存在的认知返回 None"""
        cog = self.service.get_cognition("non-existent-id")
        self.assertIsNone(cog)


class TestGraspPersistence(unittest.TestCase):
    """测试 memory 模式下的持久化行为"""

    def setUp(self):
        self.service = GraspFacade(storage_backend="memory")

    def test_storage_persistence(self):
        """验证内存存储持久化"""
        source = SourceInfo(agent_id="agent-1", task_id="task-1", channel="test")

        cog_input = CognitionInput(
            type=CognitionType.FACT,
            content="测试持久化内容确保足够长度和置信度",
            source=source,
            tags=["持久化"],
            confidence=0.9,
        )
        result = self.service.inject(cog_input)

        stored = self.service.get_cognition(result.cognition_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.content, "测试持久化内容确保足够长度和置信度")

    def test_multiple_injections_persist(self):
        """多次注入后所有数据都持久化"""
        source = SourceInfo(agent_id="agent-1", task_id="task-1", channel="test")

        ids = []
        for i in range(5):
            cog = CognitionInput(
                type=CognitionType.FACT,
                content=f"内容项编号{i}用于测试多次注入持久化",
                source=source,
                confidence=0.9,
            )
            r = self.service.inject(cog)
            ids.append(r.cognition_id)

        for cog_id in ids:
            self.assertIsNotNone(self.service.get_cognition(cog_id))

        all_cogs = self.service.list_cognitions()
        self.assertGreaterEqual(len(all_cogs), 5)


class TestGraspFilters(unittest.TestCase):
    """测试各种过滤器"""

    def setUp(self):
        self.service = GraspFacade(storage_backend="memory")
        source = SourceInfo(agent_id="agent-1", task_id="task-1", channel="test")

        self.service.inject(CognitionInput(
            type=CognitionType.FACT,
            content="事实内容A用于类型测试内容足够长",
            source=source,
            tags=["标签A"],
            confidence=0.95,
        ))
        self.service.inject(CognitionInput(
            type=CognitionType.PATTERN,
            content="模式内容B用于类型测试内容足够长",
            source=source,
            tags=["标签B"],
            confidence=0.8,
        ))
        self.service.inject(CognitionInput(
            type=CognitionType.LESSON,
            content="经验内容C用于类型测试内容足够长",
            source=source,
            tags=["标签C"],
            confidence=0.6,
        ))
        self.service.inject(CognitionInput(
            type=CognitionType.META,
            content="元认知内容D用于类型测试内容足够长",
            source=source,
            tags=["标签A", "标签B"],
            confidence=0.7,
        ))

    def test_type_filter_fact(self):
        """类型过滤 - FACT"""
        result = self.service.retrieve("", type=[CognitionType.FACT])
        self.assertEqual(result.total, 1)
        self.assertEqual(result.items[0].type, CognitionType.FACT)

    def test_type_filter_multiple(self):
        """类型过滤 - 多种类型"""
        result = self.service.retrieve("", type=[CognitionType.FACT, CognitionType.PATTERN])
        self.assertEqual(result.total, 2)

    def test_confidence_filter(self):
        """置信度过滤"""
        result = self.service.retrieve("", min_confidence=0.75)
        for item in result.items:
            self.assertGreaterEqual(item.confidence, 0.75)

    def test_tags_filter_single(self):
        """标签过滤 - 单标签"""
        result = self.service.retrieve("", tags=["标签A"])
        self.assertGreaterEqual(result.total, 1)

    def test_tags_filter_multiple_and(self):
        """标签过滤 - 多标签 AND 匹配"""
        result = self.service.retrieve("", tags=["标签A", "标签B"])
        self.assertEqual(result.total, 1)
        self.assertEqual(result.items[0].type, CognitionType.META)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Grasp Backend 单元测试")
    print("=" * 60)
    unittest.main(verbosity=2)
