"""
目标自动分解功能测试

测试 P6-02: 目标自动分解 - Goal → LLM 分解 → DAG Workflow
"""

import pytest
from unittest.mock import patch, MagicMock

from services.goal_decomposition import (
    decompose_goal,
    create_tasks_from_decomposition,
    decompose_and_create_tasks,
)


class TestDecomposeGoal:
    """测试目标分解核心逻辑"""

    @patch("reins.services.goal_decomposition.llm_service")
    def test_decompose_goal_basic(self, mock_llm_service):
        """测试基本的目标分解"""
        # 模拟 LLM 返回
        mock_llm_service.chat_completion.return_value = """
        {
            "tasks": [
                {
                    "title": "需求分析",
                    "description": "分析目标需求和约束条件",
                    "priority": "high",
                    "category": "research",
                    "depends_on": []
                },
                {
                    "title": "方案设计",
                    "description": "设计实现方案",
                    "priority": "high",
                    "category": "design",
                    "depends_on": [0]
                },
                {
                    "title": "实现开发",
                    "description": "按照方案进行开发",
                    "priority": "medium",
                    "category": "coding",
                    "depends_on": [1]
                }
            ]
        }
        """

        result = decompose_goal("测试目标", "这是一个测试目标")

        assert len(result) == 3
        assert result[0]["title"] == "需求分析"
        assert result[0]["priority"] == "high"
        assert result[0]["category"] == "research"
        assert result[0]["depends_on"] == []
        assert result[1]["depends_on"] == [0]
        assert result[2]["depends_on"] == [1]

    @patch("reins.services.goal_decomposition.llm_service")
    def test_decompose_goal_with_markdown_code_block(self, mock_llm_service):
        """测试处理 markdown 代码块格式"""
        mock_llm_service.chat_completion.return_value = """```json
        {
            "tasks": [
                {
                    "title": "任务一",
                    "description": "描述",
                    "priority": "medium",
                    "category": "coding",
                    "depends_on": []
                }
            ]
        }
        ```"""

        result = decompose_goal("测试目标")

        assert len(result) == 1
        assert result[0]["title"] == "任务一"

    @patch("reins.services.goal_decomposition.llm_service")
    def test_decompose_goal_invalid_priority(self, mock_llm_service):
        """测试无效优先级自动修正"""
        mock_llm_service.chat_completion.return_value = """
        {
            "tasks": [
                {
                    "title": "任务",
                    "description": "描述",
                    "priority": "urgent",
                    "category": "invalid",
                    "depends_on": []
                }
            ]
        }
        """

        result = decompose_goal("测试目标")

        assert len(result) == 1
        assert result[0]["priority"] == "medium"  # 被修正
        assert result[0]["category"] == "other"  # 被修正

    @patch("reins.services.goal_decomposition.llm_service")
    def test_decompose_goal_invalid_depends_on(self, mock_llm_service):
        """测试无效的 depends_on 被过滤"""
        mock_llm_service.chat_completion.return_value = """
        {
            "tasks": [
                {
                    "title": "任务1",
                    "description": "描述",
                    "priority": "medium",
                    "category": "coding",
                    "depends_on": []
                },
                {
                    "title": "任务2",
                    "description": "描述",
                    "priority": "medium",
                    "category": "coding",
                    "depends_on": [0, 5, -1]
                }
            ]
        }
        """

        result = decompose_goal("测试目标")

        assert len(result) == 2
        # 只有 0 是有效的（0 <= dep_idx < 1）
        assert result[1]["depends_on"] == [0]

    @patch("reins.services.goal_decomposition.llm_service")
    def test_decompose_goal_empty_response(self, mock_llm_service):
        """测试空响应处理"""
        mock_llm_service.chat_completion.return_value = '{"tasks": []}'

        result = decompose_goal("测试目标")

        assert result == []

    @patch("reins.services.goal_decomposition.llm_service")
    def test_decompose_goal_json_error(self, mock_llm_service):
        """测试 JSON 解析错误"""
        mock_llm_service.chat_completion.return_value = "not json"

        with pytest.raises(ValueError, match="LLM 返回格式无效"):
            decompose_goal("测试目标")


class TestCreateTasksFromDecomposition:
    """测试任务创建逻辑"""

    def test_create_tasks_basic(self, db_session):
        """测试基本任务创建"""
        goal_id = 1
        tasks_data = [
            {
                "title": "任务1",
                "description": "描述1",
                "priority": "high",
                "category": "research",
                "depends_on": [],
            },
            {
                "title": "任务2",
                "description": "描述2",
                "priority": "medium",
                "category": "coding",
                "depends_on": [0],
            },
        ]

        created_tasks = create_tasks_from_decomposition(goal_id, tasks_data, db_session)

        assert len(created_tasks) == 2
        assert created_tasks[0].title == "任务1"
        assert created_tasks[0].goal_id == goal_id
        assert created_tasks[0].status == "todo"
        assert created_tasks[1].title == "任务2"

        # 验证依赖关系
        dep_ids = [d.dependency_id for d in created_tasks[1].dependencies]
        assert created_tasks[0].id in dep_ids

    def test_create_tasks_no_dependencies(self, db_session):
        """测试无依赖任务创建"""
        tasks_data = [
            {
                "title": "独立任务",
                "description": "无依赖",
                "priority": "low",
                "category": "other",
                "depends_on": [],
            },
        ]

        created_tasks = create_tasks_from_decomposition(1, tasks_data, db_session)

        assert len(created_tasks) == 1
        assert len(created_tasks[0].dependencies) == 0

    def test_create_tasks_multiple_dependencies(self, db_session):
        """测试多依赖任务创建"""
        tasks_data = [
            {
                "title": "基础任务",
                "description": "基础",
                "priority": "high",
                "category": "research",
                "depends_on": [],
            },
            {
                "title": "依赖任务",
                "description": "依赖多个",
                "priority": "medium",
                "category": "coding",
                "depends_on": [0],
            },
        ]

        created_tasks = create_tasks_from_decomposition(1, tasks_data, db_session)

        assert len(created_tasks) == 2
        # 验证依赖关系
        dep_ids = [d.dependency_id for d in created_tasks[1].dependencies]
        assert len(dep_ids) == 1
        assert created_tasks[0].id in dep_ids


class TestDecomposeAndCreateTasks:
    """测试完整的分解流程"""

    @patch("reins.services.goal_decomposition.decompose_goal")
    @patch("reins.services.goal_decomposition.create_tasks_from_decomposition")
    def test_full_pipeline(self, mock_create, mock_decompose, db_session):
        """测试完整流程"""
        mock_decompose.return_value = [
            {
                "title": "任务1",
                "description": "描述",
                "priority": "high",
                "category": "research",
                "depends_on": [],
            }
        ]
        mock_task = MagicMock()
        mock_task.id = 1
        mock_task.title = "任务1"
        mock_create.return_value = [mock_task]

        result = decompose_and_create_tasks(
            goal_id=1,
            goal_title="测试目标",
            goal_description="描述",
            db=db_session,
        )

        mock_decompose.assert_called_once_with("测试目标", "描述")
        mock_create.assert_called_once()
        assert len(result) == 1

    @patch("reins.services.goal_decomposition.decompose_goal")
    def test_empty_decomposition_result(self, mock_decompose, db_session):
        """测试空分解结果"""
        mock_decompose.return_value = []

        result = decompose_and_create_tasks(
            goal_id=1,
            goal_title="测试目标",
            goal_description="描述",
            db=db_session,
        )

        assert result == []


# ============ 数据库 fixture ============


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    import sys
    sys.path.insert(0, "src")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.base import Base
    from models.goal import Goal
    from models.task import Task, TaskDependency

    # 使用内存数据库
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        yield session
    finally:
        session.close()
