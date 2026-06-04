"""
P6-05: 预案推荐 API 测试

覆盖:
- POST /api/v1/grasp/recommend - 预案推荐
- 推荐理由生成
- 上下文适配建议
"""

import pytest
import json
import tempfile
import shutil
import logging
import sys
from pathlib import Path

# 添加 src 到路径
src_dir = str(Path(__file__).parent.parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from fastapi.testclient import TestClient
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Test Setup
# ============================================================================

@pytest.fixture(scope="module")
def test_plans_file():
    """创建临时 plans 文件"""
    temp_dir = tempfile.mkdtemp()
    temp_file = Path(temp_dir) / "plans.jsonl"
    plans = [
        {
            "plan_id": "plan-earthquake-001",
            "title": "城市地震搜救预案",
            "description": "针对城市区域发生6.0级以上地震后的紧急搜救预案",
            "content": '{"phases": [{"name": "态势感知", "steps": ["灾情识别", "资源清点"]}, {"name": "应急响应", "steps": ["启动应急预案", "建立指挥部"]}]}',
            "tags": ["地震", "搜救", "城市"],
            "applicable_scenarios": ["城市地震", "建筑物倒塌", "7级以上地震"],
            "status": "ready",
            "version": "1.0",
            "created_at": "2026-04-10T00:00:00",
            "updated_at": "2026-04-10T00:00:00",
        },
        {
            "plan_id": "plan-flood-001",
            "title": "城市内涝应急预案",
            "description": "针对城市暴雨内涝的应急响应预案",
            "content": '{"phases": [{"name": "预警响应", "steps": ["气象监测", "水位预警"]}]}',
            "tags": ["内涝", "防汛", "城市"],
            "applicable_scenarios": ["暴雨内涝", "城市积水"],
            "status": "ready",
            "version": "1.0",
            "created_at": "2026-04-10T01:00:00",
            "updated_at": "2026-04-10T01:00:00",
        },
        {
            "plan_id": "plan-hazmat-001",
            "title": "危化品泄漏应急预案",
            "description": "危险化学品泄漏/爆炸事故处置预案",
            "content": '{"phases": [{"name": "泄漏控制", "steps": ["泄漏源定位", "围堰封堵"]}]}',
            "tags": ["危化品", "泄漏", "事故"],
            "applicable_scenarios": ["化学品泄漏", "工厂事故"],
            "status": "ready",
            "version": "1.0",
            "created_at": "2026-04-10T02:00:00",
            "updated_at": "2026-04-10T02:00:00",
        },
    ]
    with open(temp_file, "w", encoding="utf-8") as f:
        for plan in plans:
            f.write(json.dumps(plan, ensure_ascii=False) + "\n")
    yield temp_file
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def client(test_plans_file):
    """创建测试客户端"""
    import reins.api.grasp_router as gr
    original_file = gr.COGNITIONS_FILE
    # We don't need cognitions for this test, just set a valid path
    gr.COGNITIONS_FILE = Path(tempfile.mktemp())

    app = FastAPI()
    app.include_router(gr.router)
    c = TestClient(app)

    # Patch PlanStore data dir
    import grasp.plans as gp
    original_get_matcher = getattr(gp, "_test_store", None)
    original_planstore_init = gp.PlanStore.__init__

    def patched_init(self, data_dir=None):
        self._plans = {}
        self._data_file = test_plans_file
        self._load_from_file()

    gp.PlanStore.__init__ = patched_init
    yield c
    gp.PlanStore.__init__ = original_planstore_init
    gr.COGNITIONS_FILE = original_file


# ============================================================================
# Test POST /recommend
# ============================================================================

class TestPlanRecommendation:
    """P6-05: 预案推荐 API 测试"""

    def test_recommend_by_query(self, client):
        """通过查询词推荐预案"""
        response = client.post("/api/v1/grasp/recommend", json={
            "query": "地震 搜救"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["total"] > 0
        assert data["query"] == "地震 搜救"

        # 地震预案应该排在最前面
        first = data["recommendations"][0]
        assert "plan" in first
        assert "score" in first
        assert "matched_keywords" in first
        assert "reason" in first
        logger.info(f"✓ Recommend by query: {data['total']} recommendations, top score: {first['score']:.4f}")

    def test_recommend_by_goal_title(self, client):
        """通过目标标题推荐预案"""
        response = client.post("/api/v1/grasp/recommend", json={
            "goal_title": "城市地震 应急救援"  # 用空格分隔关键词
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["total"] > 0
        logger.info("✓ Recommend by goal_title works")

    def test_recommend_by_goal_description(self, client):
        """通过目标描述推荐预案"""
        response = client.post("/api/v1/grasp/recommend", json={
            "goal_description": "针对 暴雨 内涝，组织排水抢险和人员转移"  # 用空格分隔
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["total"] > 0
        logger.info("✓ Recommend by goal_description works")

    def test_recommend_with_context(self, client):
        """带上下文的推荐"""
        response = client.post("/api/v1/grasp/recommend", json={
            "query": "地震 搜救",
            "context": {
                "disaster_type": "地震",
                "response_level": "I级",
                "region": "城市"
            }
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["total"] > 0

        # 检查是否包含 context_adaptation
        first = data["recommendations"][0]
        assert "context_adaptation" in first
        assert "warnings" in first["context_adaptation"]
        logger.info(f"✓ Recommend with context: {len(first['context_adaptation']['warnings'])} warnings")

    def test_recommend_with_goal_id(self, client):
        """带 goal_id 的推荐"""
        response = client.post("/api/v1/grasp/recommend", json={
            "goal_id": "goal-disaster-001",
            "query": "地震 搜救"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["goal_id"] == "goal-disaster-001"
        logger.info("✓ Recommend with goal_id works")

    def test_recommend_limit(self, client):
        """限制返回数量"""
        response = client.post("/api/v1/grasp/recommend", json={
            "query": "地震",
            "limit": 2
        })

        assert response.status_code == 200
        data = response.json()
        assert data["total"] <= 2
        logger.info(f"✓ Recommend with limit=2: {data['total']} results")

    def test_recommend_no_query_or_goal(self, client):
        """无查询词和目标信息应返回 400"""
        response = client.post("/api/v1/grasp/recommend", json={
            "query": ""
        })

        assert response.status_code == 400
        logger.info("✓ Empty query with no goal info returns 400")

    def test_recommend_ranking_order(self, client):
        """推荐结果按分数降序排列"""
        response = client.post("/api/v1/grasp/recommend", json={
            "query": "城市"
        })

        assert response.status_code == 200
        data = response.json()
        scores = [r["score"] for r in data["recommendations"]]
        assert scores == sorted(scores, reverse=True), "Results should be sorted by score descending"
        logger.info("✓ Recommendations sorted by score descending")

    def test_recommend_match_keywords(self, client):
        """匹配关键词正确"""
        response = client.post("/api/v1/grasp/recommend", json={
            "query": "地震"
        })

        assert response.status_code == 200
        data = response.json()
        # 地震预案应该有匹配的关键词
        earthquake_rec = next((r for r in data["recommendations"]
                              if "地震" in r["plan"]["title"]), None)
        assert earthquake_rec is not None
        assert "地震" in earthquake_rec["matched_keywords"]
        logger.info("✓ Matched keywords are correct")


# ============================================================================
# Test Reason Generation
# ============================================================================

class TestReasonGeneration:
    """推荐理由生成测试"""

    def test_reason_title_match(self):
        """标题匹配生成正确理由"""
        from reins.api.grasp_router import _gen_reason
        from grasp.plans import Plan, PlanMatchResult

        plan = Plan(
            plan_id="test-001",
            title="城市地震搜救预案",
            description="测试",
            content="{}",
            tags=["测试"],
            applicable_scenarios=["测试场景"],
        )
        result = PlanMatchResult(plan=plan, score=0.9, matched_keywords=["地震", "搜救"])
        reason = _gen_reason(result)
        assert "匹配标题" in reason
        assert "高度匹配" in reason
        logger.info(f"✓ Reason for title match: {reason}")

    def test_reason_tag_match(self):
        """标签匹配生成正确理由"""
        from reins.api.grasp_router import _gen_reason
        from grasp.plans import Plan, PlanMatchResult

        plan = Plan(
            plan_id="test-002",
            title="其他预案",
            description="测试",
            content="{}",
            tags=["地震", "搜救"],
            applicable_scenarios=[],
        )
        result = PlanMatchResult(plan=plan, score=0.6, matched_keywords=["地震"])
        reason = _gen_reason(result)
        assert "匹配标签" in reason
        assert "中度匹配" in reason
        logger.info(f"✓ Reason for tag match: {reason}")

    def test_reason_partial_match(self):
        """部分匹配生成正确理由"""
        from reins.api.grasp_router import _gen_reason
        from grasp.plans import Plan, PlanMatchResult

        plan = Plan(
            plan_id="test-003",
            title="其他预案",
            description="测试",
            content="内容中提到地震相关内容",
            tags=[],
            applicable_scenarios=[],
        )
        result = PlanMatchResult(plan=plan, score=0.3, matched_keywords=["地震"])
        reason = _gen_reason(result)
        assert "部分匹配" in reason
        logger.info(f"✓ Reason for partial match: {reason}")


# ============================================================================
# Test Context Adaptation
# ============================================================================

class TestContextAdaptation:
    """上下文适配建议测试"""

    def test_adaptation_mismatch(self):
        """灾害类型不匹配时生成警告"""
        from reins.api.grasp_router import _suggest_adaptation
        from grasp.plans import Plan

        plan = Plan(
            plan_id="test-001",
            title="地震预案",
            description="测试",
            content='{"disasterType": "地震"}',
        )
        adaptation = _suggest_adaptation(plan, {
            "disaster_type": "洪水",
            "response_level": "I级",
            "region": "山区",
        })
        assert len(adaptation["warnings"]) > 0
        assert len(adaptation["notes"]) > 0
        logger.info(f"✓ Adaptation warnings: {adaptation['warnings']}")

    def test_adaptation_match(self):
        """灾害类型匹配时无警告"""
        from reins.api.grasp_router import _suggest_adaptation
        from grasp.plans import Plan

        plan = Plan(
            plan_id="test-002",
            title="地震预案",
            description="测试",
            content='{"disasterType": "地震", "responseLevel": "I级"}',
        )
        adaptation = _suggest_adaptation(plan, {
            "disaster_type": "地震",
            "response_level": "I级",
        })
        assert len(adaptation["warnings"]) == 0
        logger.info("✓ Adaptation: no warnings when types match")

    def test_adaptation_empty_context(self):
        """空上下文无警告"""
        from reins.api.grasp_router import _suggest_adaptation
        from grasp.plans import Plan

        plan = Plan(
            plan_id="test-003",
            title="测试预案",
            description="测试",
            content="{}",
        )
        adaptation = _suggest_adaptation(plan, {})
        assert len(adaptation["warnings"]) == 0
        assert len(adaptation["notes"]) == 0
        logger.info("✓ Empty context produces no warnings")


# ============================================================================
# Test Router Registration
# ============================================================================

class TestRecommendRouter:
    """推荐路由注册测试"""

    def test_recommend_endpoint_exists(self):
        """推荐端点已注册"""
        from reins.api.grasp_router import router
        paths = [r.path for r in router.routes]
        assert "/api/v1/grasp/recommend" in paths or "/recommend" in paths
        logger.info("✓ POST /recommend endpoint registered")
