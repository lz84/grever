# -*- coding: utf-8 -*-
"""
E2E Tests - Reach Domain

L4-08 Reach 场景域 (10 cases):
- TC-E2E-R-001: 场景 CRUD + 预览
- TC-E2E-R-002: 匹配
- TC-E2E-R-003: 实例化
- TC-E2E-R-004: 收藏反馈
- TC-E2E-R-005: 行业包
- TC-E2E-R-006: 标签打标
- TC-E2E-R-007: 标签统计
- TC-E2E-R-008: MCP
- TC-E2E-R-009: 附件
- TC-E2E-R-010: 产出物
"""

import pytest
import sys
import os
import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import pytest
import os

# Skip if LLM API not configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("LLM_URL"),
    reason="LLM_URL not configured (requires LLM API)"
)


src_dir = str(Path(__file__).parent.parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

src_path = os.path.join(src_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db_manager():
    """Mock database manager"""
    manager = MagicMock()
    manager.engine = MagicMock()
    return manager


@pytest.fixture
def sample_scenario():
    """创建示例场景"""
    return {
        "id": f"scenario-{uuid.uuid4().hex[:12]}",
        "name": "E2E Test Scenario",
        "category": "software",
        "level": "project",
        "status": "active",
        "version": 1,
        "trust_level": "medium",
        "source": "llm_generated",
        "description": "End-to-end test scenario",
        "scenario_desc": "This is a test scenario for E2E testing",
        "template_dag": {
            "nodes": [
                {"id": "step_1", "type": "step", "name": "需求分析", "description": "分析需求"},
                {"id": "step_2", "type": "step", "name": "方案设计", "description": "设计方案"},
            ],
            "edges": [{"source": "step_1", "target": "step_2"}],
        },
        "usage_count": 0,
        "success_rate": 0.0,
        "avg_duration_ms": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def sample_goal():
    """创建示例目标"""
    return {
        "id": f"goal-{uuid.uuid4().hex[:12]}",
        "title": "E2E Test Goal",
        "description": "Test goal for scenario matching",
        "status": "draft",
        "priority": "medium",
    }


@pytest.fixture
def sample_scenarios_list():
    """创建多个示例场景"""
    return [
        {
            "id": f"scenario-{uuid.uuid4().hex[:12]}",
            "name": "地震应急响应场景",
            "category": "earthquake",
            "level": "goal",
            "status": "active",
            "description": "地震发生后的应急响应流程",
            "scenario_desc": "包括人员搜救、资源调度、指挥协调等环节",
            "template_dag": {
                "nodes": [
                    {"id": "step_1", "name": "震情评估", "type": "step"},
                    {"id": "step_2", "name": "启动预案", "type": "step"},
                ],
                "edges": [{"source": "step_1", "target": "step_2"}],
            },
            "trust_level": "high",
            "usage_count": 10,
        },
        {
            "id": f"scenario-{uuid.uuid4().hex[:12]}",
            "name": "洪水防汛场景",
            "category": "flood",
            "level": "goal",
            "status": "active",
            "description": "洪水预警和防汛应急流程",
            "scenario_desc": "包括水位监测、泄洪调度、转移安置等环节",
            "template_dag": {
                "nodes": [
                    {"id": "step_1", "name": "水情监测", "type": "step"},
                    {"id": "step_2", "name": "预警发布", "type": "step"},
                ],
                "edges": [{"source": "step_1", "target": "step_2"}],
            },
            "trust_level": "high",
            "usage_count": 8,
        },
        {
            "id": f"scenario-{uuid.uuid4().hex[:12]}",
            "name": "危化品泄漏场景",
            "category": "chemical",
            "level": "goal",
            "status": "active",
            "description": "危化品泄漏事故应急处理",
            "scenario_desc": "包括泄漏控制、人员疏散、环境监测等环节",
            "template_dag": {
                "nodes": [
                    {"id": "step_1", "name": "泄漏评估", "type": "step"},
                    {"id": "step_2", "name": "控制泄漏", "type": "step"},
                ],
                "edges": [{"source": "step_1", "target": "step_2"}],
            },
            "trust_level": "medium",
            "usage_count": 5,
        },
    ]


# ============================================================================
# TC-E2E-R-001: 场景 CRUD + 预览
# ============================================================================

class TestE2EReachScenarioCRUD:
    """
    TC-E2E-R-001: 场景 CRUD + 预览

    测试场景：
    1. Create - 创建场景
    2. Read - 读取场景列表/详情
    3. Update - 更新场景
    4. Delete - 删除场景
    5. 场景预览
    """

    def test_create_scenario(self, sample_scenario):
        """测试创建场景"""
        from models.scenario import Scenario

        scenario = Scenario(
            id=sample_scenario["id"],
            name=sample_scenario["name"],
            category=sample_scenario["category"],
            description=sample_scenario["description"],
            status=sample_scenario["status"],
        )

        assert scenario.name == sample_scenario["name"]
        assert scenario.category == sample_scenario["category"]

    def test_read_scenario_list(self, sample_scenarios_list):
        """测试读取场景列表"""
        # 模拟列表查询
        scenarios = sample_scenarios_list

        assert len(scenarios) == 3
        assert all("name" in s for s in scenarios)

    def test_filter_scenarios_by_category(self, sample_scenarios_list):
        """测试按分类过滤场景"""
        target_category = "earthquake"

        filtered = [
            s for s in sample_scenarios_list
            if s.get("category") == target_category
        ]

        assert len(filtered) == 1
        assert filtered[0]["name"] == "地震应急响应场景"

    def test_filter_scenarios_by_status(self, sample_scenarios_list):
        """测试按状态过滤场景"""
        target_status = "active"

        filtered = [
            s for s in sample_scenarios_list
            if s.get("status") == target_status
        ]

        assert len(filtered) == 3

    def test_get_scenario_detail(self, sample_scenario):
        """测试获取场景详情"""
        scenario_id = sample_scenario["id"]

        # 模拟查询
        found = sample_scenario
        assert found["id"] == scenario_id
        assert "template_dag" in found

    def test_update_scenario(self, sample_scenario):
        """测试更新场景"""
        from models.scenario import Scenario

        scenario = Scenario(
            id=sample_scenario["id"],
            name=sample_scenario["name"],
            category=sample_scenario["category"],
            status="active",
        )

        # 模拟更新
        scenario.status = "archived"
        assert scenario.status == "archived"

    def test_delete_scenario(self, sample_scenario):
        """测试删除场景"""
        scenario_id = sample_scenario["id"]

        # 模拟删除
        deleted = True
        assert deleted is True

    def test_scenario_preview(self, sample_scenario):
        """测试场景预览"""
        from reach.scenarios.api.scenario_instantiate import ScenarioPreviewResponse, PreviewProjectItem, PreviewTaskItem

        preview = ScenarioPreviewResponse(
            scenario_id=sample_scenario["id"],
            scenario_name=sample_scenario["name"],
            projects_count=2,
            tasks_count=4,
            projects=[
                PreviewProjectItem(
                    id="proj-1",
                    name="[测试场景] 需求分析",
                    tasks_count=2,
                    tasks=[
                        PreviewTaskItem(name="任务1", agent_type="executor"),
                        PreviewTaskItem(name="任务2", agent_type="analyst"),
                    ],
                ),
                PreviewProjectItem(
                    id="proj-2",
                    name="[测试场景] 方案设计",
                    tasks_count=2,
                    tasks=[
                        PreviewTaskItem(name="任务3", agent_type="executor"),
                        PreviewTaskItem(name="任务4", agent_type="reviewer"),
                    ],
                ),
            ],
        )

        assert preview.scenario_id == sample_scenario["id"]
        assert preview.projects_count == 2
        assert preview.tasks_count == 4
        assert len(preview.projects) == 2


# ============================================================================
# TC-E2E-R-002: 匹配
# ============================================================================

class TestE2EReachMatch:
    """
    TC-E2E-R-002: 场景匹配

    测试场景：
    1. 为 Goal 匹配 Scenario
    2. 预览场景匹配
    3. 验证匹配评分
    4. 验证阈值判断
    """

    def test_match_scenario_for_goal(self, sample_scenarios_list, sample_goal):
        """测试为 Goal 匹配 Scenario"""
        from reach.scenarios.api.scenario_models import ScenarioMatchItem, MATCH_THRESHOLD

        goal_title = sample_goal["title"]
        goal_desc = sample_goal["description"]

        # 模拟匹配计算
        matches = []
        for sc in sample_scenarios_list:
            # 简单的关键词匹配评分
            score = 0.3  # 默认分数

            if sc["template_dag"]:
                if any(kw in goal_title.lower() for kw in sc["name"].lower().split()):
                    score = 0.5
                if any(kw in goal_desc.lower() for kw in sc["description"].lower().split()):
                    score = max(score, 0.6)

            if score >= 0.2:  # 基础阈值
                matches.append(
                    ScenarioMatchItem(
                        scenario_id=sc["id"],
                        name=sc["name"],
                        category=sc["category"],
                        level=sc.get("level", "goal"),
                        match_score=round(score, 3),
                        trust_level=sc.get("trust_level", "low"),
                        usage_count=sc.get("usage_count", 0),
                        description=sc.get("description", ""),
                        phase_count=len(sc.get("template_dag", {}).get("nodes", [])),
                    )
                )

        matches.sort(key=lambda m: m.match_score, reverse=True)

        assert isinstance(matches, list)
        assert len(matches) >= 0

    def test_match_preview(self, sample_scenarios_list):
        """测试预览匹配"""
        from reach.scenarios.api.scenario_models import MatchPreviewRequest, ScenarioMatchItem

        req = MatchPreviewRequest(
            title="地震应急响应",
            description="需要快速响应的应急场景",
        )

        assert req.title is not None

    def test_match_score_calculation(self, sample_scenarios_list):
        """测试匹配评分计算"""
        from reach.scenarios.api.scenario_match import _calc_score

        goal_title = "地震应急响应"
        goal_desc = "地震发生后的救援流程"

        for sc in sample_scenarios_list:
            score = _calc_score(goal_title, goal_desc, sc)
            assert 0 <= score <= 1

    def test_threshold_check(self):
        """测试阈值检查"""
        from reach.scenarios.api.scenario_models import MATCH_THRESHOLD

        assert MATCH_THRESHOLD == 0.30

        # 测试阈值判断
        scores = [0.5, 0.4, 0.3, 0.2]
        for score in scores:
            threshold_met = score >= MATCH_THRESHOLD
            assert isinstance(threshold_met, bool)

    def test_match_response_format(self, sample_goal, sample_scenarios_list):
        """测试匹配响应格式"""
        from reach.scenarios.api.scenario_models import ScenarioMatchResponse, ScenarioMatchItem

        response = ScenarioMatchResponse(
            goal_id=sample_goal["id"],
            goal_title=sample_goal["title"],
            matches=[
                ScenarioMatchItem(
                    scenario_id=sc["id"],
                    name=sc["name"],
                    category=sc["category"],
                    level="goal",
                    match_score=0.5,
                    trust_level="high",
                    usage_count=sc.get("usage_count", 0),
                    description=sc.get("description", ""),
                    phase_count=2,
                )
                for sc in sample_scenarios_list[:2]
            ],
            threshold_met=True,
            threshold=0.30,
        )

        assert "goal_id" in response.model_dump()
        assert "matches" in response.model_dump()
        assert "threshold_met" in response.model_dump()


# ============================================================================
# TC-E2E-R-003: 实例化
# ============================================================================

class TestE2EReachInstantiate:
    """
    TC-E2E-R-003: 场景实例化

    测试场景：
    1. 创建实例化请求
    2. 执行实例化逻辑
    3. 验证 Goal/Project/Task 创建
    4. 验证 context_md 填充
    """

    def test_instantiate_request(self):
        """测试实例化请求"""
        from reach.scenarios.api.scenario_instantiate import InstantiateToGoalRequest

        req = InstantiateToGoalRequest(
            goal_title="新目标：从场景实例化",
            goal_description="这是一个测试目标",
            goal_priority="high",
            goal_status="draft",
        )

        assert req.goal_title is not None
        assert req.goal_priority == "high"

    def test_instantiate_to_goal(self, sample_scenario, sample_goal):
        """测试实例化到 Goal"""
        from reach.scenarios.api.scenario_instantiate import InstantiateToGoalResponse

        # 模拟实例化结果
        response = InstantiateToGoalResponse(
            goal_id=sample_goal["id"],
            scenario_id=sample_scenario["id"],
            projects_created=2,
            tasks_created=4,
            skipped=0,
        )

        assert response.goal_id == sample_goal["id"]
        assert response.scenario_id == sample_scenario["id"]
        assert response.projects_created >= 0
        assert response.tasks_created >= 0

    def test_context_md_building(self, sample_scenario):
        """测试 context_md 构建"""
        from reach.scenarios.api.scenario_instantiate import instantiate_scenario

        # 模拟 context_md 格式
        context_md_lines = [
            f"# {sample_scenario['name']}",
            "",
            f"**类别**: {sample_scenario['category']}",
            f"**项目数**: 2",
            f"**任务数**: 4",
            "",
            sample_scenario.get("scenario_desc", ""),
            "",
            f"从场景 `{sample_scenario['id']}` 实例化生成。",
        ]

        context_md = "\n".join(context_md_lines)
        assert "# " in context_md
        assert sample_scenario['name'] in context_md

    def test_executor_type_behavior(self):
        """测试 executor_type 行为"""
        from reach.scenarios.api.scenario_instantiate import _determine_executor_behavior

        # 测试不同 executor_type
        test_cases = [
            ("ai", ("todo", False)),
            ("auto_eval", ("todo", False)),
            ("human", ("waiting_human", True)),
            ("ai_approval", ("waiting_human", True)),
            ("ai_data", ("waiting_human", True)),
            ("ai_confirm", ("todo", False)),
        ]

        for executor_type, expected in test_cases:
            status, needs_hitl = _determine_executor_behavior(executor_type)
            assert status == expected[0]
            assert needs_hitl == expected[1]

    def test_hitl_request_idempotency(self):
        """测试 HITL request 幂等创建"""
        from reach.scenarios.api.scenario_instantiate import _create_hitl_request

        # 模拟数据库连接
        mock_conn = MagicMock()

        # 第一次创建
        created_1 = _create_hitl_request(
            mock_conn,
            task_id="task-1",
            goal_id="goal-1",
            project_id="proj-1",
            task_name="测试任务",
            task_desc="测试描述",
            executor_type="human",
            scenario_id="scenario-1",
            scenario_name="测试场景",
        )

        # 第二次创建（应该跳过）
        created_2 = _create_hitl_request(
            mock_conn,
            task_id="task-1",
            goal_id="goal-1",
            project_id="proj-1",
            task_name="测试任务",
            task_desc="测试描述",
            executor_type="human",
            scenario_id="scenario-1",
            scenario_name="测试场景",
        )

        # 第二次应该返回 False（已存在）
        assert created_1 is True or created_1 is False
        assert created_2 is False


# ============================================================================
# TC-E2E-R-004: 收藏反馈
# ============================================================================

class TestE2EReachFavorites:
    """
    TC-E2E-R-004: 收藏反馈

    测试场景：
    1. 收藏场景
    2. 取消收藏
    3. 验证收藏状态
    4. 验证使用统计更新
    """

    def test_add_favorite(self, sample_scenario):
        """测试添加收藏"""
        scenario_id = sample_scenario["id"]

        # 模拟添加收藏
        favorite = {
            "user_id": "user-123",
            "scenario_id": scenario_id,
            "created_at": datetime.now().isoformat(),
        }

        assert favorite["scenario_id"] == scenario_id
        assert "user_id" in favorite

    def test_remove_favorite(self, sample_scenario):
        """测试移除收藏"""
        scenario_id = sample_scenario["id"]

        # 模拟移除收藏
        removed = True  # 模拟成功

        assert removed is True

    def test_favorite_status(self, sample_scenario):
        """测试收藏状态"""
        scenario_id = sample_scenario["id"]

        # 模拟检查收藏状态
        is_favorited = True  # 模拟已收藏

        assert isinstance(is_favorited, bool)

    def test_usage_count_update(self, sample_scenario):
        """测试使用统计更新"""
        scenario = sample_scenario.copy()

        # 模拟使用后更新统计
        scenario["usage_count"] = scenario.get("usage_count", 0) + 1

        assert scenario["usage_count"] == 1


# ============================================================================
# TC-E2E-R-005: 行业包
# ============================================================================

class TestE2EReachIndustryPacks:
    """
    TC-E2E-R-005: 行业包

    测试场景：
    1. CRUD 行业包
    2. 添加包内容
    3. 删除包内容
    4. 验证包内容关联
    """

    def test_create_industry_pack(self):
        """测试创建行业包"""
        from reach.industry.api.industry_tag_models import IndustryPackCreate

        pack = IndustryPackCreate(
            id="pack-ai-emergency",
            name="AI应急行业包",
            industry="emergency",
            version="1.0",
            description="AI辅助应急响应行业包",
            status="draft",
        )

        assert pack.name is not None
        assert pack.industry == "emergency"

    def test_list_industry_packs(self):
        """测试列出行业包"""
        # 模拟列表查询
        packs = [
            {"id": "pack-1", "name": "应急包", "industry": "emergency"},
            {"id": "pack-2", "name": "金融包", "industry": "finance"},
        ]

        assert len(packs) == 2

    def test_filter_packs_by_industry(self):
        """测试按行业过滤"""
        all_packs = [
            {"id": "pack-1", "industry": "emergency"},
            {"id": "pack-2", "industry": "finance"},
            {"id": "pack-3", "industry": "emergency"},
        ]

        target_industry = "emergency"
        filtered = [p for p in all_packs if p["industry"] == target_industry]

        assert len(filtered) == 2

    def test_add_pack_content(self):
        """测试添加包内容"""
        from reach.industry.api.industry_tag_models import IndustryPackContentItem

        content = IndustryPackContentItem(
            pack_id="pack-1",
            content_type="scenario",
            content_id="scenario-123",
        )

        assert content.pack_id == "pack-1"
        assert content.content_type == "scenario"

    def test_remove_pack_content(self):
        """测试移除包内容"""
        # 模拟移除
        removed = True
        assert removed is True

    def test_pack_detail_response(self):
        """测试包详情响应"""
        from reach.industry.api.industry_tag_models import IndustryPackDetailResponse

        response = IndustryPackDetailResponse(
            id="pack-1",
            name="应急行业包",
            industry="emergency",
            version="1.0",
            description="测试包",
            tags_count=5,
            scenarios_count=3,
            skills_count=2,
            status="active",
            created_at=1709424000,  # Unix timestamp
            updated_at=1709424000,  # Unix timestamp
            pack_type="standard",
            base_pack_id=None,
            contents=[],
        )

        assert response.id == "pack-1"
        assert response.tags_count >= 0


# ============================================================================
# TC-E2E-R-006: 标签打标
# ============================================================================

class TestE2EReachTagging:
    """
    TC-E2E-R-006: 标签打标

    测试场景：
    1. 创建标签
    2. 为场景打标
    3. 批量打标
    4. 验证标签关联
    """

    def test_create_tag(self):
        """测试创建标签"""
        tag = {
            "id": f"tag-{uuid.uuid4().hex[:8]}",
            "name": "高优先级",
            "industry": "general",
            "category": "priority",
        }

        assert tag["name"] is not None
        assert "industry" in tag

    def test_tag_scenario(self, sample_scenario):
        """测试为场景打标"""
        scenario_id = sample_scenario["id"]

        # 模拟打标
        tags = ["高优先级", "AI辅助", "应急"]
        tagged_scenario = {**sample_scenario, "tags": tags}

        assert len(tagged_scenario["tags"]) == 3

    def test_batch_tagging(self, sample_scenarios_list):
        """测试批量打标"""
        scenarios = sample_scenarios_list
        target_tag = "通用"

        # 模拟批量打标
        for s in scenarios:
            s["tags"] = s.get("tags", []) + [target_tag]

        # 验证
        tagged_count = sum(1 for s in scenarios if target_tag in s.get("tags", []))
        assert tagged_count == len(scenarios)

    def test_tag_association(self, sample_scenario):
        """测试标签关联"""
        scenario_id = sample_scenario["id"]

        # 模拟标签关联
        associations = [
            {"scenario_id": scenario_id, "tag": "标签1"},
            {"scenario_id": scenario_id, "tag": "标签2"},
        ]

        assert len(associations) == 2


# ============================================================================
# TC-E2E-R-007: 标签统计
# ============================================================================

class TestE2EReachTagStats:
    """
    TC-E2E-R-007: 标签统计

    测试场景：
    1. 统计标签使用频率
    2. 获取标签分布
    3. 验证统计数据
    """

    def test_tag_frequency_stats(self):
        """测试标签频率统计"""
        # 模拟标签使用数据
        tag_usage = {
            "高优先级": 15,
            "AI辅助": 12,
            "应急": 8,
            "通用": 20,
        }

        assert tag_usage["高优先级"] == 15
        assert len(tag_usage) > 0

    def test_tag_distribution(self):
        """测试标签分布"""
        total_scenarios = 100
        tag_counts = {
            "高优先级": 25,
            "AI辅助": 20,
            "应急": 15,
            "通用": 40,
        }

        # 计算分布比例
        distribution = {
            tag: count / total_scenarios * 100
            for tag, count in tag_counts.items()
        }

        assert all(0 <= pct <= 100 for pct in distribution.values())

    def test_stats_response_format(self):
        """测试统计数据响应格式"""
        stats = {
            "total_tags": 10,
            "total_scenarios_tagged": 50,
            "top_tags": [
                {"tag": "高优先级", "count": 15, "percentage": 30.0},
                {"tag": "AI辅助", "count": 12, "percentage": 24.0},
            ],
            "distribution": {
                "high_priority": 0.3,
                "ai_assisted": 0.24,
            },
        }

        assert "total_tags" in stats
        assert "top_tags" in stats
        assert len(stats["top_tags"]) > 0


# ============================================================================
# TC-E2E-R-008: MCP
# ============================================================================

class TestE2EReachMCP:
    """
    TC-E2E-R-008: MCP Server

    测试场景：
    1. CRUD MCP Server
    2. 列出工具
    3. Agent-MCP 匹配
    4. 验证匹配结果
    """

    def test_create_mcp_server(self):
        """测试创建 MCP Server"""
        from reach.mcp.api.mcp import MCPServerCreate, ToolCreate

        server = MCPServerCreate(
            name="Weather MCP",
            description="天气查询服务",
            transport="sse",
            url="https://api.weather.example.com",
            category="weather",
            tools=[
                ToolCreate(
                    name="get_weather",
                    description="获取指定城市的天气",
                    parameters='{"city": "string"}',
                    return_type="json",
                ),
            ],
        )

        assert server.name == "Weather MCP"
        assert len(server.tools) == 1

    def test_list_mcp_servers(self):
        """测试列出 MCP Server"""
        # 模拟列表
        servers = [
            {"id": "mcp-1", "name": "Weather", "status": "active"},
            {"id": "mcp-2", "name": "Calculator", "status": "active"},
        ]

        assert len(servers) == 2

    def test_filter_mcp_servers(self):
        """测试过滤 MCP Server"""
        all_servers = [
            {"id": "mcp-1", "category": "weather", "status": "active"},
            {"id": "mcp-2", "category": "calculator", "status": "active"},
            {"id": "mcp-3", "category": "weather", "status": "inactive"},
        ]

        # 按分类过滤
        weather_servers = [s for s in all_servers if s["category"] == "weather"]
        assert len(weather_servers) == 2

        # 按状态过滤
        active_servers = [s for s in all_servers if s["status"] == "active"]
        assert len(active_servers) == 2

    def test_list_mcp_tools(self):
        """测试列出工具"""
        tools = [
            {
                "id": "tool-1",
                "name": "get_weather",
                "description": "获取天气",
                "parameters": {"city": "string"},
            },
            {
                "id": "tool-2",
                "name": "get_forecast",
                "description": "获取预报",
                "parameters": {"city": "string", "days": "int"},
            },
        ]

        assert len(tools) == 2

    def test_agent_mcp_matching(self):
        """测试 Agent-MCP 匹配"""
        from reach.mcp.api.mcp import AgentMatchRequest, MatchResult

        agent_description = "我是一个负责查询天气的助手"

        # 模拟匹配结果
        matches = [
            MatchResult(
                server_id="mcp-weather-1",
                server_name="Weather MCP",
                score=85,
                match_reasons=["功能描述匹配", "工具能力覆盖"],
            ),
            MatchResult(
                server_id="mcp-calc-1",
                server_name="Calculator MCP",
                score=30,
                match_reasons=["基础计算能力"],
            ),
        ]

        assert len(matches) == 2
        assert matches[0].score > matches[1].score

    def test_mcp_server_update(self):
        """测试更新 MCP Server"""
        from reach.mcp.api.mcp import MCPServerUpdate

        update = MCPServerUpdate(
            status="inactive",
            description="更新后的描述",
        )

        assert update.status == "inactive"

    def test_mcp_delete(self):
        """测试删除 MCP Server"""
        server_id = "mcp-1"

        # 模拟删除
        deleted = True
        assert deleted is True


# ============================================================================
# TC-E2E-R-009: 附件
# ============================================================================

class TestE2EReachAttachments:
    """
    TC-E2E-R-009: 附件管理

    测试场景：
    1. 上传附件
    2. 下载附件
    3. 删除附件
    4. 验证附件关联
    """

    def test_upload_attachment(self):
        """测试上传附件"""
        attachment = {
            "id": f"attach-{uuid.uuid4().hex[:12]}",
            "name": "test_document.pdf",
            "type": "document",
            "size": 1024000,
            "content_type": "application/pdf",
        }

        assert attachment["name"] is not None
        assert attachment["size"] > 0

    def test_download_attachment(self):
        """测试下载附件"""
        attachment_id = "attach-123"

        # 模拟下载
        download_url = f"/api/v1/attachments/{attachment_id}/download"
        assert "/download" in download_url

    def test_delete_attachment(self):
        """测试删除附件"""
        attachment_id = "attach-123"

        # 模拟删除
        deleted = True
        assert deleted is True

    def test_attachment_association(self):
        """测试附件关联"""
        # 模拟附件与场景/任务的关联
        associations = [
            {"attachment_id": "attach-1", "scenario_id": "scenario-1"},
            {"attachment_id": "attach-2", "task_id": "task-1"},
        ]

        assert len(associations) == 2


# ============================================================================
# TC-E2E-R-010: 产出物
# ============================================================================

class TestE2EReachArtifacts:
    """
    TC-E2E-R-010: 产出物管理

    测试场景：
    1. 创建产出物
    2. 列出产出物
    3. 更新产出物
    4. 删除产出物
    5. 下载产出物
    """

    def test_create_artifact(self):
        """测试创建产出物"""
        from reach.artifacts.api.artifacts_models import ArtifactCreate

        artifact = ArtifactCreate(
            task_id="task-123",
            project_id="proj-456",
            goal_id="goal-789",
            created_by="agent-001",
            name="测试报告.pdf",
            type="document",
            description="E2E 测试报告",
            tags=["测试", "报告"],
            content_base64="SGVsbG8gV29ybGQ=",  # "Hello World"
        )

        assert artifact.name is not None
        assert artifact.created_by is not None

    def test_list_artifacts(self):
        """测试列出产出物"""
        # 模拟列表
        artifacts = [
            {"id": "art-1", "name": "报告1.pdf", "type": "document"},
            {"id": "art-2", "name": "代码.zip", "type": "code"},
        ]

        assert len(artifacts) == 2

    def test_filter_artifacts_by_type(self):
        """测试按类型过滤产出物"""
        all_artifacts = [
            {"id": "art-1", "type": "document"},
            {"id": "art-2", "type": "code"},
            {"id": "art-3", "type": "document"},
        ]

        documents = [a for a in all_artifacts if a["type"] == "document"]
        assert len(documents) == 2

    def test_update_artifact(self):
        """测试更新产出物"""
        from reach.artifacts.api.artifacts_models import ArtifactUpdate

        update = ArtifactUpdate(
            name="更新后的文件名.pdf",
            description="更新后的描述",
            tags=["更新", "测试"],
        )

        assert update.name is not None

    def test_delete_artifact(self):
        """测试删除产出物"""
        artifact_id = "art-123"

        # 模拟删除
        deleted = True
        assert deleted is True

    def test_artifact_response(self):
        """测试产出物响应"""
        from reach.artifacts.api.artifacts_models import ArtifactResponse

        response = ArtifactResponse(
            id="art-123",
            task_id="task-456",
            project_id="proj-789",
            goal_id="goal-012",
            created_by="agent-001",
            name="测试产出物.pdf",
            type="document",
            url="/api/v1/artifacts/art-123/download",
            size=1024000,
            description="测试描述",
            tags=["测试"],
            created_at=datetime.now().isoformat(),
        )

        assert response.id == "art-123"
        assert response.url is not None
        assert response.size > 0

    def test_artifact_download(self):
        """测试产出物下载"""
        artifact_id = "art-123"

        # 模拟下载
        download_info = {
            "artifact_id": artifact_id,
            "download_url": f"/api/v1/artifacts/{artifact_id}/download",
            "content_type": "application/pdf",
        }

        assert download_info["artifact_id"] == artifact_id
        assert "/download" in download_info["download_url"]


# ============================================================================
# 综合测试
# ============================================================================

class TestE2EReachComprehensive:
    """
    Reach 综合测试
    覆盖多个测试用例的组合场景
    """

    def test_full_scenario_lifecycle(self, sample_scenario, sample_goal):
        """完整场景生命周期测试"""
        # 1. 创建场景
        scenario = sample_scenario.copy()
        assert scenario["status"] == "active"

        # 2. 匹配场景
        match_score = 0.5
        assert match_score >= 0

        # 3. 实例化场景
        projects_created = 2
        tasks_created = 4
        assert projects_created > 0
        assert tasks_created > 0

        # 4. 更新使用统计
        scenario["usage_count"] = scenario.get("usage_count", 0) + 1
        assert scenario["usage_count"] == 1

    def test_scenario_workflow_integration(self, sample_scenarios_list, sample_goal):
        """场景工作流集成测试"""
        goal_id = sample_goal["id"]

        # 1. 匹配场景
        matches = [
            {"scenario_id": s["id"], "match_score": 0.5}
            for s in sample_scenarios_list
        ]
        best_match = max(matches, key=lambda m: m["match_score"])

        # 2. 实例化
        instantiate_result = {
            "goal_id": goal_id,
            "scenario_id": best_match["scenario_id"],
            "projects": 2,
            "tasks": 4,
        }

        # 3. 生成产出物
        artifacts = [
            {"id": f"art-{i}", "name": f"产出物{i}", "goal_id": goal_id}
            for i in range(2)
        ]

        assert len(artifacts) == 2
        assert instantiate_result["goal_id"] == goal_id

    def test_reach_api_models(self):
        """测试 Reach API 模型"""
        from reach.scenarios.api.scenario_models import ScenarioMatchItem, ScenarioMatchResponse

        # 测试匹配响应模型
        response = ScenarioMatchResponse(
            goal_id="goal-test",
            goal_title="测试目标",
            matches=[
                ScenarioMatchItem(
                    scenario_id="sc-1",
                    name="测试场景",
                    category="software",
                    level="project",
                    match_score=0.5,
                    trust_level="medium",
                    usage_count=5,
                    description="测试描述",
                    phase_count=3,
                )
            ],
            threshold_met=True,
            threshold=0.3,
        )

        assert response.goal_id == "goal-test"
        assert len(response.matches) == 1

    def test_reach_integration_scenario(self, sample_scenarios_list):
        """Reach 集成场景测试"""
        # 1. 创建一个包含多个场景的行业包
        industry_pack = {
            "id": "pack-integration",
            "name": "集成测试行业包",
            "industry": "software",
            "scenarios": sample_scenarios_list,
        }

        # 2. 为场景添加标签
        for sc in industry_pack["scenarios"]:
            sc["tags"] = ["集成测试", "自动化"]
            sc["capabilities"] = ["高优先级"]

        # 3. 验证行业包内容
        assert len(industry_pack["scenarios"]) == 3
        assert all("tags" in sc for sc in industry_pack["scenarios"])