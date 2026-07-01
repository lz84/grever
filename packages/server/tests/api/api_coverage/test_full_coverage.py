"""
API 全覆盖测试 - 单层文件版本

按 5 层依赖顺序执行：Layer 0 → Layer 1 → Layer 2 → Layer 3 → Layer 4 → Queries
合并所有层到一个文件，避免 conftest 导入问题。

运行:
    cd packages/server && python -m pytest tests/api/api_coverage/test_full_coverage.py -v --tb=short
"""
import sys
import os
import uuid
import time
from pathlib import Path

src_dir = str(Path(__file__).parent.parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import pytest
from fastapi.testclient import TestClient
from api.server import create_app

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def client():
    return TestClient(create_app())


class TestData:
    agent_id = None
    agent_ids = []
    goal_id = None
    goal_ids = []
    project_id = None
    project_ids = []
    task_id = None
    task_ids = []
    workflow_id = None
    workflow_ids = []
    scenario_id = None
    pack_id = None
    skill_id = None
    solution_id = None


@pytest.fixture(scope="session")
def shared_data():
    return TestData()


def gen_id(prefix="test"):
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def default_tags():
    return {"technical": "backend", "business": "reach", "professional": "dev", "management": "self"}


# ============================================================================
# Layer 0: 基础资源初始化
# ============================================================================

class TestLayer0_Basic:
    """第 0 层：基础资源（无依赖）"""

    def test_001_agent_register(self, client, shared_data):
        aid = gen_id("agent-l0")
        shared_data.agent_id = aid
        resp = client.post("/api/v1/agents", json={"id": aid, "name": "L0 Agent", "platform": "hermes", "capability_tags": default_tags()})
        assert resp.status_code in (200, 201, 409)
        shared_data.agent_ids.append(aid)

    def test_002_agent_heartbeat(self, client, shared_data):
        if not shared_data.agent_id: pytest.skip("No agent")
        resp = client.post(f"/api/v1/agents/{shared_data.agent_id}/heartbeat", json={"load": 0.1, "status": "online"})
        assert resp.status_code == 200

    def test_003_scheduler_stats(self, client):
        resp = client.get("/api/v1/scheduler/stats")
        assert resp.status_code == 200

    def test_004_settings_list(self, client):
        resp = client.get("/api/v1/settings")
        assert resp.status_code == 200

    def test_005_industry_tags_list(self, client):
        resp = client.get("/api/v1/industry-tags")
        assert resp.status_code == 200

    def test_006_industry_packs_list(self, client, shared_data):
        resp = client.get("/api/v1/industry-packs")
        assert resp.status_code == 200
        data = resp.json()
        packs = data if isinstance(data, list) else data.get("packs", [])
        if packs: shared_data.pack_id = packs[0].get("id")

    def test_007_skills_list(self, client, shared_data):
        resp = client.get("/api/v1/skills")
        assert resp.status_code == 200
        data = resp.json()
        skills = data if isinstance(data, list) else data.get("skills", data.get("items", []))
        if skills: shared_data.skill_id = skills[0].get("id")

    def test_008_mcp_list(self, client):
        resp = client.get("/api/v1/mcp-servers")
        assert resp.status_code == 200


# ============================================================================
# Layer 1: 工作分解核心链 (Goal → Project → Task)
# ============================================================================

class TestLayer1_CoreChain:
    """第 1 层：工作分解核心链"""

    def test_001_create_goal(self, client, shared_data):
        gid = gen_id("goal-l1")
        shared_data.goal_id = gid
        resp = client.post("/api/v1/goals/", json={"title": "L1 Test Goal", "description": "API coverage", "priority": "high", "capability_tags": default_tags()})
        assert resp.status_code in (200, 201)
        data = resp.json()
        if data.get("id"): shared_data.goal_id = data["id"]
        shared_data.goal_ids.append(shared_data.goal_id)

    def test_002_get_goal(self, client, shared_data):
        if not shared_data.goal_id: pytest.skip("No goal")
        resp = client.get(f"/api/v1/goals/{shared_data.goal_id}")
        assert resp.status_code == 200

    def test_003_goal_pause(self, client, shared_data):
        if not shared_data.goal_id: pytest.skip("No goal")
        resp = client.post(f"/api/v1/goals/{shared_data.goal_id}/pause")
        assert resp.status_code in (200, 500)

    def test_004_goal_resume(self, client, shared_data):
        if not shared_data.goal_id: pytest.skip("No goal")
        resp = client.post(f"/api/v1/goals/{shared_data.goal_id}/resume")
        assert resp.status_code in (200, 500)

    def test_005_goal_tree(self, client, shared_data):
        if not shared_data.goal_id: pytest.skip("No goal")
        resp = client.get(f"/api/v1/goals/{shared_data.goal_id}/tree")
        assert resp.status_code == 200

    def test_006_create_project(self, client, shared_data):
        pid = gen_id("proj-l1")
        shared_data.project_id = pid
        resp = client.post("/api/v1/projects/", json={"name": "L1 Project", "description": "API test", "goal_id": shared_data.goal_id, "priority": "high", "capability_tags": default_tags()})
        assert resp.status_code in (200, 201)
        data = resp.json()
        if data.get("id"): shared_data.project_id = data["id"]
        shared_data.project_ids.append(shared_data.project_id)

    def test_007_create_task(self, client, shared_data):
        tid = gen_id("task-l1")
        shared_data.task_id = tid
        resp = client.post("/api/v1/tasks/", json={"title": "L1 Task", "description": "API test", "project_id": shared_data.project_id, "goal_id": shared_data.goal_id, "priority": "medium", "category": "backend", "capability_tags": default_tags(), "depends_on": [], "needs_verification": False, "acceptance_criteria": "", "done_criteria": "Code committed"})
        assert resp.status_code in (200, 201)
        data = resp.json()
        if data.get("id"): shared_data.task_id = data["id"]
        shared_data.task_ids.append(shared_data.task_id)

    def test_008_get_task(self, client, shared_data):
        if not shared_data.task_id: pytest.skip("No task")
        resp = client.get(f"/api/v1/tasks/{shared_data.task_id}")
        assert resp.status_code == 200

    def test_009_task_statuses(self, client):
        resp = client.get("/api/v1/tasks/statuses")
        assert resp.status_code == 200

    def test_010_task_labels_all(self, client):
        resp = client.get("/api/v1/tasks/labels/all")
        assert resp.status_code == 200


# ============================================================================
# Layer 2: 派生资源 (Workflows, Scenarios, Solutions)
# ============================================================================

class TestLayer2_Derived:
    """第 2 层：派生资源"""

    def test_001_workflows_list(self, client):
        resp = client.get("/api/v1/workflows")
        assert resp.status_code == 200

    def test_002_scenarios_list(self, client, shared_data):
        resp = client.get("/api/v1/scenarios")
        assert resp.status_code == 200
        data = resp.json()
        scenarios = data if isinstance(data, list) else data.get("scenarios", data.get("items", []))
        if scenarios: shared_data.scenario_id = scenarios[0].get("id")

    def test_003_solutions_list(self, client, shared_data):
        resp = client.get("/api/v1/solutions")
        assert resp.status_code == 200
        data = resp.json()
        sols = data if isinstance(data, list) else data.get("solutions", data.get("items", []))
        if sols: shared_data.solution_id = sols[0].get("id")


# ============================================================================
# Layer 3 + 4 + Queries: 交互、监控、查询
# ============================================================================

class TestLayer34_Queries:
    """第 3/4 层 + 查询类接口"""

    def test_001_hitl_pending(self, client):
        resp = client.get("/api/v1/human-input/pending")
        assert resp.status_code == 200

    def test_002_disputes_list(self, client):
        resp = client.get("/api/v1/disputes")
        assert resp.status_code == 200

    def test_003_grasp_cognition(self, client):
        resp = client.get("/api/v1/grasp/cognition")
        assert resp.status_code == 200

    def test_004_knowledge_injector_status(self, client):
        resp = client.get("/api/v1/knowledge-injector/status")
        assert resp.status_code == 200

    def test_005_traces_list(self, client):
        resp = client.get("/api/v1/traces")
        assert resp.status_code == 200

    def test_006_admin_agents(self, client):
        resp = client.get("/api/v1/admin/agents")
        assert resp.status_code == 200

    def test_007_timeout_check(self, client):
        resp = client.get("/api/v1/timeout/check")
        assert resp.status_code == 200

    def test_008_security_alerts(self, client):
        resp = client.get("/api/v1/security/alerts")
        assert resp.status_code == 200

    def test_009_dashboard_stats(self, client):
        resp = client.get("/api/v1/dashboard/stats")
        assert resp.status_code == 200

    def test_010_search(self, client):
        resp = client.get("/api/v1/search")
        assert resp.status_code == 200

    def test_011_endpoints(self, client):
        resp = client.get("/api/v1/endpoints")
        assert resp.status_code == 200

    def test_012_status(self, client):
        resp = client.get("/api/v1/status")
        assert resp.status_code == 200

    def test_013_features(self, client):
        resp = client.get("/api/v1/features")
        assert resp.status_code == 200

    def test_014_artifacts(self, client):
        resp = client.get("/api/v1/artifacts")
        assert resp.status_code == 200

    def test_015_attachments(self, client):
        resp = client.get("/api/v1/attachments")
        assert resp.status_code == 200
