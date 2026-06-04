"""
P6-01: 知识注入 API 测试

覆盖:
- POST /api/v1/grasp/cognition - 知识注入
- GET /api/v1/grasp/knowledge - 列出认知
- GET /api/v1/grasp/cognition/{id} - 获取认知
- DELETE /api/v1/grasp/cognition/{id} - 删除认知
- PATCH /api/v1/grasp/cognition/{id} - 更新认知
- GET /api/v1/grasp/cognition-assessment/{agent_id} - 认知评估
"""

import pytest
import json
import tempfile
import shutil
import logging
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

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
def test_cognitions_file():
    """创建临时 cognitions 文件"""
    temp_dir = tempfile.mkdtemp()
    temp_file = Path(temp_dir) / "test_cognitions.jsonl"
    # 写入一些测试数据
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "cognition_id": "cog-test-001",
            "type": "lesson",
            "content": "地震救援中发现主干道堵塞会影响医疗点设立",
            "tags": ["地震", "救援"],
            "confidence": 0.9,
            "source": {"agent_id": "agent-rescue-01", "task_id": "task-006", "channel": "nexus"},
            "status": "published",
            "domain": "抢险救灾",
            "quality_score": 1.0,
            "version": 1,
            "created_at": "2026-04-14T00:00:00+00:00",
            "updated_at": "2026-04-14T00:00:00+00:00",
        }, ensure_ascii=False) + "\n")
        f.write(json.dumps({
            "cognition_id": "cog-test-002",
            "type": "pattern",
            "content": "危化品泄漏事故中，疏散范围应根据化学品类型和泄漏量动态调整",
            "tags": ["危化品", "疏散"],
            "confidence": 0.85,
            "source": {"agent_id": "agent-hazmat-01", "task_id": "task-hz-003", "channel": "nexus"},
            "status": "published",
            "domain": "抢险救灾",
            "quality_score": 0.95,
            "version": 1,
            "created_at": "2026-04-14T00:01:00+00:00",
            "updated_at": "2026-04-14T00:01:00+00:00",
        }, ensure_ascii=False) + "\n")
    yield temp_file
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def client(test_cognitions_file):
    """创建测试客户端"""
    app = FastAPI()
    from reins.api.grasp_router import router as grasp_router
    
    # Patch the cognitions file path
    import reins.api.grasp_router as gr
    gr.COGNITIONS_FILE = test_cognitions_file
    
    app.include_router(grasp_router)
    return TestClient(app)


# ============================================================================
# Test POST /cognition - 知识注入
# ============================================================================

class TestKnowledgeInjection:
    """P6-01: 知识注入 API 测试"""

    def test_create_cognition_lesson(self, client):
        """注入 lesson 类型认知"""
        response = client.post("/api/v1/grasp/cognition", json={
            "type": "lesson",
            "content": "搜救过程中发现，使用生命探测仪配合搜救犬可以提高废墟下的生命发现率",
            "source": {
                "agent_id": "agent-rescue-01",
                "task_id": "task-001",
                "channel": "nexus"
            },
            "tags": ["搜救", "生命探测", "经验"],
            "confidence": 0.88,
            "domain": "抢险救灾"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "cognition" in data
        assert data["cognition"]["type"] == "lesson"
        assert data["cognition"]["source"]["agent_id"] == "agent-rescue-01"
        assert data["cognition"]["source"]["channel"] == "nexus"
        logger.info("✓ POST /cognition - lesson type created successfully")

    def test_create_cognition_fact(self, client):
        """注入 fact 类型认知"""
        response = client.post("/api/v1/grasp/cognition", json={
            "type": "fact",
            "content": "6.0级以上地震后，倒塌建筑中存活率在前72小时显著下降",
            "source": {
                "agent_id": "agent-rescue-01",
                "task_id": "task-001",
                "channel": "nexus"
            },
            "tags": ["地震", "黄金救援时间"],
            "confidence": 0.95,
            "domain": "抢险救灾"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["cognition"]["type"] == "fact"
        assert data["cognition"]["confidence"] == 0.95
        logger.info("✓ POST /cognition - fact type created successfully")

    def test_create_cognition_pattern(self, client):
        """注入 pattern 类型认知"""
        response = client.post("/api/v1/grasp/cognition", json={
            "type": "pattern",
            "content": "大型灾害救援中，多Agent协同的效率比单Agent高3-5倍",
            "source": {
                "agent_id": "agent-coordinator-01",
                "task_id": "task-coord-001",
                "channel": "nexus"
            },
            "tags": ["协同", "效率"],
            "confidence": 0.8,
            "domain": "抢险救灾"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["cognition"]["type"] == "pattern"
        logger.info("✓ POST /cognition - pattern type created successfully")

    def test_create_cognition_meta(self, client):
        """注入 meta 类型认知"""
        response = client.post("/api/v1/grasp/cognition", json={
            "type": "meta",
            "content": "知识注入API应在Sprint 6完成，作为Grasp和Nexus的桥梁",
            "source": {
                "agent_id": "system",
                "task_id": "MAK-169",
                "channel": "api"
            },
            "tags": ["元认知", "项目管理"],
            "confidence": 1.0,
            "domain": "系统"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["cognition"]["type"] == "meta"
        logger.info("✓ POST /cognition - meta type created successfully")

    def test_create_cognition_nexus_source(self, client):
        """注入认知 - source 包含 Nexus 执行结果信息"""
        response = client.post("/api/v1/grasp/cognition", json={
            "type": "lesson",
            "content": "执行task-006时发现主干道疏通是后续任务的依赖瓶颈",
            "source": {
                "agent_id": "agent-infra-01",
                "task_id": "task-006",
                "channel": "nexus"
            },
            "tags": ["基础设施", "依赖", "经验"],
            "confidence": 0.9,
            "domain": "抢险救灾",
            "metadata": {
                "original_task_status": "done",
                "lessons_learned": True
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["cognition"]["source"]["channel"] == "nexus"
        assert data["cognition"]["metadata"]["lessons_learned"] == True
        logger.info("✓ POST /cognition - Nexus source with execution result")

    def test_create_cognition_missing_content(self, client):
        """注入认知 - 缺少内容应返回 400"""
        response = client.post("/api/v1/grasp/cognition", json={
            "type": "lesson",
            "content": "",
            "source": {"agent_id": "test"}
        })
        
        assert response.status_code == 400
        logger.info("✓ POST /cognition - empty content rejected")

    def test_create_cognition_invalid_type(self, client):
        """注入认知 - 非法类型应返回 400"""
        response = client.post("/api/v1/grasp/cognition", json={
            "type": "invalid_type",
            "content": "测试内容",
            "source": {}
        })
        
        assert response.status_code == 400
        logger.info("✓ POST /cognition - invalid type rejected")

    def test_create_cognition_invalid_confidence(self, client):
        """注入认知 - 非法置信度应返回 400"""
        response = client.post("/api/v1/grasp/cognition", json={
            "type": "fact",
            "content": "测试内容",
            "confidence": 1.5,
            "source": {}
        })
        
        assert response.status_code == 400
        logger.info("✓ POST /cognition - invalid confidence rejected")

    def test_create_cognition_content_too_short(self, client):
        """注入认知 - 内容太短应标记为 pending_review"""
        response = client.post("/api/v1/grasp/cognition", json={
            "type": "fact",
            "content": "短",
            "confidence": 0.2,  # low confidence + short = quality < 0.5
            "source": {"agent_id": "test"}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["cognition"]["status"] == "pending_review"
        assert data["cognition"]["quality_score"] < 0.5
        logger.info("✓ POST /cognition - short content marked as pending_review")

    def test_create_cognition_dangerous_content(self, client):
        """注入认知 - 危险内容应被拒绝"""
        response = client.post("/api/v1/grasp/cognition", json={
            "type": "fact",
            "content": "test execute(system('rm -rf /'))",
            "source": {"agent_id": "test"}
        })
        
        assert response.status_code == 400
        logger.info("✓ POST /cognition - dangerous content rejected")

    def test_create_cognition_with_tags(self, client):
        """注入认知 - 带标签"""
        response = client.post("/api/v1/grasp/cognition", json={
            "type": "lesson",
            "content": "地震救援中应先评估建筑结构再进行搜救",
            "source": {"agent_id": "agent-rescue-01", "channel": "nexus"},
            "tags": ["地震", "搜救", "建筑评估", "优先级"],
            "confidence": 0.9
        })
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["cognition"]["tags"]) == 4
        logger.info("✓ POST /cognition - tags stored correctly")

    def test_create_cognition_auto_fields(self, client):
        """注入认知 - 自动生成的字段正确"""
        response = client.post("/api/v1/grasp/cognition", json={
            "type": "lesson",
            "content": "测试自动生成字段",
            "source": {"agent_id": "test-agent", "task_id": "test-task", "channel": "nexus"},
            "confidence": 0.8
        })
        
        assert response.status_code == 200
        data = response.json()
        cog = data["cognition"]
        
        # 自动生成字段
        assert cog["cognition_id"].startswith("cog-")
        assert cog["status"] == "published"
        assert cog["quality_score"] >= 0.5
        assert cog["version"] == 1
        assert "created_at" in cog
        assert "updated_at" in cog
        logger.info("✓ POST /cognition - auto fields correct")


# ============================================================================
# Test GET /knowledge - 列出认知
# ============================================================================

class TestListKnowledge:
    """GET /knowledge 测试"""

    def test_list_all_knowledge(self, client):
        """列出所有认知"""
        response = client.get("/api/v1/grasp/knowledge")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["cognitions"]) >= 2  # 至少2条测试数据
        logger.info(f"✓ GET /knowledge - {len(data['cognitions'])} cognitions returned")

    def test_filter_by_type(self, client):
        """按类型过滤"""
        response = client.get("/api/v1/grasp/knowledge?type=lesson")
        
        assert response.status_code == 200
        data = response.json()
        for c in data["cognitions"]:
            assert c["type"] == "lesson"
        logger.info("✓ GET /knowledge?type=lesson - filter works")

    def test_filter_by_tag(self, client):
        """按标签过滤"""
        response = client.get("/api/v1/grasp/knowledge?tag=地震")
        
        assert response.status_code == 200
        data = response.json()
        for c in data["cognitions"]:
            assert any("地震" in t for t in c.get("tags", []))
        logger.info("✓ GET /knowledge?tag=地震 - tag filter works")

    def test_filter_by_multiple_tags(self, client):
        """多标签过滤（OR 逻辑）"""
        response = client.get("/api/v1/grasp/knowledge?tag=地震&tag=危化品")
        
        assert response.status_code == 200
        data = response.json()
        for c in data["cognitions"]:
            tags = [t.lower() for t in c.get("tags", [])]
            assert "地震" in tags or "危化品" in tags
        logger.info("✓ GET /knowledge?tag=地震&tag=危化品 - multi-tag filter works")


# ============================================================================
# Test GET /cognition/{id} - 获取认知
# ============================================================================

class TestGetCognition:
    """GET /cognition/{id} 测试"""

    def test_get_existing_cognition(self, client):
        """获取已存在的认知"""
        response = client.get("/api/v1/grasp/cognition/cog-test-001")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["cognition"]["cognition_id"] == "cog-test-001"
        logger.info("✓ GET /cognition/{id} - existing cognition found")

    def test_get_nonexistent_cognition(self, client):
        """获取不存在的认知返回 404"""
        response = client.get("/api/v1/grasp/cognition/cog-nonexistent")
        
        assert response.status_code == 404
        logger.info("✓ GET /cognition/{id} - nonexistent returns 404")


# ============================================================================
# Test DELETE /cognition/{id} - 删除认知
# ============================================================================

class TestDeleteCognition:
    """DELETE /cognition/{id} 测试"""

    def test_delete_cognition(self, client):
        """删除认知"""
        # 先创建一个
        create_response = client.post("/api/v1/grasp/cognition", json={
            "type": "fact",
            "content": "这条认知将被删除",
            "source": {"agent_id": "test"},
            "confidence": 0.8
        })
        assert create_response.status_code == 200
        cog_id = create_response.json()["cognition"]["cognition_id"]
        
        # 删除
        delete_response = client.delete(f"/api/v1/grasp/cognition/{cog_id}")
        assert delete_response.status_code == 200
        
        # 验证已删除
        get_response = client.get(f"/api/v1/grasp/cognition/{cog_id}")
        assert get_response.status_code == 404
        logger.info("✓ DELETE /cognition/{id} - delete works")

    def test_delete_nonexistent_cognition(self, client):
        """删除不存在的认知返回 404"""
        response = client.delete("/api/v1/grasp/cognition/cog-does-not-exist")
        assert response.status_code == 404
        logger.info("✓ DELETE /cognition/{id} - nonexistent returns 404")


# ============================================================================
# Test GET /cognition-assessment/{agent_id} - 认知评估
# ============================================================================

class TestCognitionAssessment:
    """GET /cognition-assessment/{agent_id} 测试"""

    def test_cognition_assessment(self, client):
        """获取 Agent 的认知评估"""
        response = client.get("/api/v1/grasp/cognition-assessment/agent-rescue-01")
        
        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data or "agent_id" in data
        logger.info("✓ GET /cognition-assessment/{agent_id} - assessment returned")

    def test_cognition_assessment_no_data(self, client):
        """无数据的 Agent 认知评估"""
        response = client.get("/api/v1/grasp/cognition-assessment/nonexistent-agent")
        
        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data or "agent_id" in data
        logger.info("✓ GET /cognition-assessment - no data agent returns assessment")


# ============================================================================
# Test Router Registration
# ============================================================================

class TestRouterRegistration:
    """路由注册测试"""

    def test_router_prefix(self):
        """路由前缀正确"""
        from reins.api.grasp_router import router
        assert router.prefix == "/api/v1/grasp"
        logger.info("✓ Grasp router prefix is /api/v1/grasp")

    def test_all_routes_exist(self):
        """所有期望的路由都存在"""
        from reins.api.grasp_router import router
        paths = {r.path: r.methods for r in router.routes}
        
        expected_routes = {
            "/cognition": {"POST"},
            "/knowledge": {"GET"},
            "/graph": {"GET"},
            "/cognition/{cognition_id}": {"GET", "DELETE", "PATCH"},
            "/cognition-assessment/{agent_id}": {"GET"},
        }
        
        for path, methods in expected_routes.items():
            full_path = f"/api/v1/grasp{path}"
            assert full_path in paths, f"Missing route: {full_path}"
        logger.info(f"✓ All {len(expected_routes)} expected routes registered")


# ============================================================================
# Summary
# ============================================================================

class TestKnowledgeInjectionIntegration:
    """知识注入集成场景测试"""

    def test_nexus_execution_result_to_knowledge(self, client):
        """
        集成场景：Nexus 执行结果 → Grasp 知识库
        
        模拟场景：
        1. Nexus 执行完一个救援任务
        2. 任务完成后自动生成经验认知
        3. 认知写入 Grasp 知识库
        4. 认知可被后续任务检索
        """
        # 步骤1: 模拟 Nexus 执行结果写入认知
        response = client.post("/api/v1/grasp/cognition", json={
            "type": "lesson",
            "content": "在城市地震救援中，主干道疏通（task-006）是所有后续任务的依赖，应作为最高优先级执行。疏通完成后，医疗点设立和避难所设置才能并行开展。",
            "source": {
                "agent_id": "agent-infra-01",
                "task_id": "task-006",
                "workflow_id": "wf-disaster-001",
                "channel": "nexus",
                "execution_result": "completed",
                "auto_generated": True
            },
            "tags": ["地震", "基础设施", "依赖管理", "优先级"],
            "confidence": 0.92,
            "domain": "抢险救灾",
            "metadata": {
                "workflow_name": "城市地震应急响应",
                "lesson_category": "dependency_management",
                "generated_from": "execution_result"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        cog = data["cognition"]
        assert cog["source"]["channel"] == "nexus"
        assert cog["source"]["task_id"] == "task-006"
        
        # 步骤2: 验证认知可通过知识库检索
        search_response = client.get("/api/v1/grasp/knowledge?type=lesson&tag=基础设施")
        assert search_response.status_code == 200
        search_data = search_response.json()
        matching = [c for c in search_data["cognitions"] 
                   if "主干道疏通" in c.get("content", "")]
        assert len(matching) > 0
        assert matching[0]["source"]["task_id"] == "task-006"
        
        logger.info("✓ Integration: Nexus execution result → Grasp knowledge base → retrieval")
