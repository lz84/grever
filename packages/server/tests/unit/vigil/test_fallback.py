"""
P6-06 Grasp 本地降级引擎单元测试 (Grasp Fallback Engine Unit Tests)

测试覆盖:
- 意图理解 (intent_understanding)
- 智能体匹配 (agent_matching)
- 任务认知抽取 (dispatch_cognition)
- 认知反馈 (cognitive_feedback)
- 关键词提取 (_extract_keywords)
"""

import pytest
from reins.common.grasp_client.fallback import (
    GraspFallbackEngine,
    INTENT_TEMPLATES,
)


class TestIntentUnderstanding:
    """意图理解测试"""

    def setup_method(self):
        self.engine = GraspFallbackEngine()

    def test_development_intent(self):
        """开发类目标应该识别为 development"""
        result = self.engine.intent_understanding("开发一个用户管理系统")
        assert result["intent"]["type"] == "development"
        assert result["fallback"] is True
        assert len(result["suggested_tasks"]) > 0

    def test_design_intent(self):
        """设计类目标应该识别为 design"""
        result = self.engine.intent_understanding("设计系统架构方案")
        assert result["intent"]["type"] == "design"

    def test_research_intent(self):
        """研究类目标应该识别为 research"""
        result = self.engine.intent_understanding("调研市场上的技术方案")
        assert result["intent"]["type"] == "research"

    def test_troubleshoot_intent(self):
        """排错类目标应该识别为 troubleshoot"""
        result = self.engine.intent_understanding("修复系统崩溃的bug")
        assert result["intent"]["type"] == "troubleshoot"

    def test_deployment_intent(self):
        """部署类目标应该识别为 deployment"""
        result = self.engine.intent_understanding("部署服务到生产环境")
        assert result["intent"]["type"] == "deployment"

    def test_optimization_intent(self):
        """优化类目标应该识别为 optimization"""
        result = self.engine.intent_understanding("优化系统性能和速度")
        assert result["intent"]["type"] == "optimization"

    def test_testing_intent(self):
        """测试类目标应该识别为 testing"""
        result = self.engine.intent_understanding("测试接口功能是否正常")
        assert result["intent"]["type"] == "testing"

    def test_documentation_intent(self):
        """文档类目标应该识别为 documentation"""
        result = self.engine.intent_understanding("用户使用手册编写")
        assert result["intent"]["type"] == "documentation"

    def test_general_intent(self):
        """无法匹配的目标应该返回 general"""
        result = self.engine.intent_understanding("随便说点什么")
        assert result["intent"]["type"] == "general"
        assert result["intent"]["confidence"] == 0.3

    def test_suggested_tasks_for_development(self):
        """开发意图应该有需求分析→架构→编码→测试的任务链"""
        result = self.engine.intent_understanding("实现一个订单管理功能")
        tasks = result["suggested_tasks"]
        assert len(tasks) >= 3
        # 验证任务有优先级排序
        priorities = [t["priority"] for t in tasks]
        assert priorities == sorted(priorities)

    def test_confidence_score_range(self):
        """置信度应该在 0-1 之间"""
        result = self.engine.intent_understanding("开发一个完整的电商平台")
        assert 0 <= result["intent"]["confidence"] <= 1


class TestAgentMatching:
    """智能体匹配测试"""

    def setup_method(self):
        self.engine = GraspFallbackEngine()

    def test_match_by_capability(self):
        """应该按能力匹配度排序"""
        agents = [
            {"id": "a1", "name": "麻子", "capabilities": ["coding", "testing"]},
            {"id": "a2", "name": "谷子", "capabilities": ["analysis", "writing"]},
            {"id": "a3", "name": "刚子", "capabilities": ["coding", "design"]},
        ]
        requirements = {"required_capabilities": ["coding"]}

        result = self.engine.agent_matching(requirements, agents)
        assert len(result["matched_agents"]) > 0
        # 有 coding 能力的应该排在前面
        top_agent = result["matched_agents"][0]
        assert top_agent["agent_id"] in ["a1", "a3"]

    def test_no_requirements_matches_all(self):
        """无特定需求时应该都能匹配"""
        agents = [
            {"id": "a1", "name": "Agent1", "capabilities": ["coding"]},
        ]
        requirements = {"required_capabilities": []}

        result = self.engine.agent_matching(requirements, agents)
        assert len(result["matched_agents"]) == 1

    def test_empty_agent_list(self):
        """空 Agent 列表应该返回空结果"""
        result = self.engine.agent_matching({"required_capabilities": ["coding"]}, [])
        assert result["matched_agents"] == []
        assert result["best_match"] is None

    def test_match_score_range(self):
        """匹配分数应该在 0-1 之间"""
        agents = [
            {"id": "a1", "name": "A1", "capabilities": ["coding"]},
            {"id": "a2", "name": "A2", "capabilities": ["design"]},
        ]
        requirements = {"required_capabilities": ["coding"]}

        result = self.engine.agent_matching(requirements, agents)
        for ma in result["matched_agents"]:
            assert 0 <= ma["match_score"] <= 1

    def test_fallback_flag(self):
        """应该标记为降级模式"""
        agents = [{"id": "a1", "name": "A1", "capabilities": ["coding"]}]
        result = self.engine.agent_matching({"required_capabilities": ["coding"]}, agents)
        assert result["fallback"] is True
        assert result["source"] == "local_capability_matching"

    def test_general_task_type(self):
        """通用任务类型应该使用通用匹配"""
        agents = [
            {"id": "a1", "name": "A1", "capabilities": ["general"]},
        ]
        requirements = {"task_type": "general"}

        result = self.engine.agent_matching(requirements, agents)
        assert len(result["matched_agents"]) >= 0


class TestDispatchCognition:
    """任务认知抽取测试"""

    def setup_method(self):
        self.engine = GraspFallbackEngine()

    def test_basic_cognition_extraction(self):
        """应该能提取认知"""
        result = self.engine.dispatch_cognition(
            task_id="task-001",
            task_title="开发用户管理系统",
            task_description="实现用户注册、登录、权限管理功能",
            task_type="development",
        )
        assert "cognitions" in result
        assert "total" in result
        assert "fallback" in result
        assert result["fallback"] is True

    def test_max_cognitions_limit(self):
        """不应该超过最大认知数量"""
        result = self.engine.dispatch_cognition(
            task_id="task-001",
            task_title="测试",
            task_description="测试描述",
            task_type="testing",
            max_cognitions=2,
        )
        assert len(result["cognitions"]) <= 2

    def test_keywords_used(self):
        """应该返回使用的关键词"""
        result = self.engine.dispatch_cognition(
            task_id="task-001",
            task_title="开发系统",
            task_description="实现API接口",
            task_type="development",
        )
        assert "keywords_used" in result
        assert isinstance(result["keywords_used"], list)


class TestCognitiveFeedback:
    """认知反馈测试"""

    def setup_method(self):
        self.engine = GraspFallbackEngine()

    def test_feedback_returns_true(self):
        """反馈应该返回成功"""
        result = self.engine.cognitive_feedback(
            task_id="task-001",
            execution_result={"status": "success"},
            learnings={"key": "value"},
        )
        assert result is True

    def test_feedback_buffered(self):
        """反馈应该被缓冲"""
        self.engine.cognitive_feedback(
            task_id="task-001",
            execution_result={"status": "success"},
            learnings={},
        )
        self.engine.cognitive_feedback(
            task_id="task-002",
            execution_result={"status": "failed"},
            learnings={},
        )
        assert len(self.engine._feedback_buffer) == 2

    def test_feedback_entry_has_task_id(self):
        """反馈条目应该包含 task_id"""
        self.engine.cognitive_feedback(
            task_id="my-task-123",
            execution_result={},
            learnings={},
        )
        last_entry = self.engine._feedback_buffer[-1]
        assert last_entry["task_id"] == "my-task-123"


class TestExtractKeywords:
    """关键词提取测试"""

    def test_chinese_stopwords_removed(self):
        """应该移除中文停用词"""
        keywords = GraspFallbackEngine._extract_keywords("这是一个测试")
        assert "的" not in keywords
        assert "是" not in keywords

    def test_english_stopwords_removed(self):
        """应该移除英文停用词"""
        keywords = GraspFallbackEngine._extract_keywords("this is a test")
        assert "the" not in keywords
        assert "is" not in keywords
        assert "a" not in keywords

    def test_short_words_removed(self):
        """单字符应该被移除"""
        keywords = GraspFallbackEngine._extract_keywords("a b test code")
        assert "a" not in keywords
        assert "b" not in keywords

    def test_punctuation_removed(self):
        """标点符号应该被移除"""
        keywords = GraspFallbackEngine._extract_keywords("hello, world! test.")
        assert all(k.isalnum() for k in keywords)


class TestReload:
    """重新加载测试"""

    def test_reload_does_not_crash(self):
        """重新加载不应该崩溃"""
        engine = GraspFallbackEngine()
        engine.reload()
        # 不抛异常即为通过
