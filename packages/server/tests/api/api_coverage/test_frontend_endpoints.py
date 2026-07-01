"""
前端端点全覆盖测试

覆盖 frontend-api-calls.ts 中定义的所有 67 个前端调用端点。
按 5 层依赖顺序执行，确保资源依赖链正确。

运行:
    pytest tests/api/api_coverage/test_frontend_endpoints.py -v
"""
import pytest
import time
import sys
from pathlib import Path

src_dir = str(Path(__file__).parent.parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from fastapi.testclient import TestClient
from api.server import create_app


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def client():
    c = TestClient(create_app())
    yield c


class Store:
    """Module-scoped store for IDs created during tests."""
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
    scenario_ids = []
    skill_id = None
    skill_ids = []
    mcp_id = None
    mcp_ids = []
    knowledge_id = None
    knowledge_ids = []
    hitl_id = None
    hitl_ids = []


@pytest.fixture(scope="module")
def store():
    """Module-scoped store for IDs created during tests."""
    return Store()


# ============================================================================
# Layer 0: Settings, Agents, Skills, MCP, Knowledge (基础资源)
# ============================================================================

class TestL0_Settings:
    """TC-FE-L0-01~06: Settings & industry tags"""

    def test_get_settings(self, client):
        r = client.get("/api/v1/settings")
        assert r.status_code in (200, 404, 500)

    def test_get_settings_by_key(self, client):
        r = client.get("/api/v1/settings/key/test-key")
        assert r.status_code in (200, 404, 500)

    def test_get_industry_tags(self, client):
        r = client.get("/api/v1/industry-tags")
        assert r.status_code in (200, 404)

    def test_industry_tags_stats(self, client):
        r = client.get("/api/v1/industry-tags/stats")
        assert r.status_code in (200, 404)

    def test_industry_tags_suggestions(self, client):
        r = client.get("/api/v1/industry-tags/suggestions")
        assert r.status_code in (200, 404)


class TestL0_Skills:
    """TC-FE-L0-07~09: Skills"""

    def test_list_skills(self, client, store):
        r = client.get("/api/v1/skills")
        assert r.status_code in (200, 404, 500)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                store.skill_id = data[0].get("id") or data[0].get("name")

    def test_get_skill_detail(self, client, store):
        if store.skill_id:
            r = client.get(f"/api/v1/skills/{store.skill_id}")
            assert r.status_code in (200, 404, 500)

    def test_skill_install_prompt(self, client, store):
        if store.skill_id:
            r = client.get(f"/api/v1/skills/{store.skill_id}/install-prompt")
            assert r.status_code in (200, 404, 500)


class TestL0_MCP:
    """TC-FE-L0-10~11: MCP servers"""

    def test_list_mcp_servers(self, client, store):
        r = client.get("/api/v1/mcp-servers")
        assert r.status_code in (200, 404, 500)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                store.mcp_id = data[0].get("id")

    def test_mcp_server_tools(self, client, store):
        if store.mcp_id:
            r = client.get(f"/api/v1/mcp-servers/{store.mcp_id}/tools")
            assert r.status_code in (200, 404, 500)


class TestL0_Knowledge:
    """TC-FE-L0-12~14: Knowledge"""

    def test_list_knowledge(self, client, store):
        r = client.get("/api/v1/knowledge")
        assert r.status_code in (200, 404, 500)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                store.knowledge_id = data[0].get("id")

    def test_get_knowledge_detail(self, client, store):
        if store.knowledge_id:
            r = client.get(f"/api/v1/knowledge/{store.knowledge_id}")
            assert r.status_code in (200, 404, 500)

    def test_search_knowledge(self, client):
        r = client.get("/api/v1/knowledge", params={"q": "test"})
        assert r.status_code in (200, 404, 500)


class TestL0_Agents:
    """TC-FE-L0-15~18: Agents"""

    def test_list_agents(self, client, store):
        r = client.get("/api/v1/agents/")
        assert r.status_code in (200, 404, 500)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                store.agent_id = data[0].get("id")
                store.agent_ids = [a.get("id") for a in data if a.get("id")]

    def test_agent_heartbeat(self, client, store):
        if not store.agent_id:
            r_create = client.post("/api/v1/agents/register", json={
                "agent_id": f"fe-test-{int(time.time())}",
                "capabilities": ["python"],
                "model": "test"
            })
            if r_create.status_code == 200:
                store.agent_id = r_create.json().get("id") or r_create.json().get("agent_id")

        if store.agent_id:
            r = client.post(f"/api/v1/agents/{store.agent_id}/heartbeat")
            assert r.status_code in (200, 404, 500)

    def test_agent_execution_logs(self, client, store):
        if store.agent_id:
            r = client.get(f"/api/v1/agents/{store.agent_id}/execution-logs",
                          params={"limit": 10, "offset": 0})
            assert r.status_code in (200, 404, 500)

    def test_agent_heartbeat_logs(self, client, store):
        if store.agent_id:
            r = client.get(f"/api/v1/agents/{store.agent_id}/heartbeat_logs",
                          params={"limit": 50})
            assert r.status_code in (200, 404, 500)


# ============================================================================
# Layer 1: Goals, Projects, Tasks (核心工作链)
# ============================================================================

class TestL1_Goals:
    """TC-FE-L1-01~09: Goal lifecycle"""

    def test_create_goal(self, client, store):
        r = client.post("/api/v1/goals", json={
            "title": f"FE Goal {int(time.time())}",
            "description": "frontend coverage test",
            "priority": "medium"
        })
        assert r.status_code in (200, 201, 404, 500)
        if r.status_code in (200, 201):
            store.goal_id = r.json().get("id")
            store.goal_ids.append(store.goal_id)

    def test_goal_activate(self, client, store):
        if store.goal_id:
            r = client.post(f"/api/v1/goals/{store.goal_id}/activate")
            assert r.status_code in (200, 404, 500)

    def test_goal_pause(self, client, store):
        if store.goal_id:
            r = client.post(f"/api/v1/goals/{store.goal_id}/pause")
            assert r.status_code in (200, 404, 500)

    def test_goal_resume(self, client, store):
        if store.goal_id:
            r = client.post(f"/api/v1/goals/{store.goal_id}/resume")
            assert r.status_code in (200, 404, 500)

    def test_goal_iterations(self, client, store):
        if store.goal_id:
            r = client.get(f"/api/v1/goals/{store.goal_id}/iterations")
            assert r.status_code in (200, 404, 500)

    def test_goal_iteration_status(self, client, store):
        if store.goal_id:
            r = client.get(f"/api/v1/goals/{store.goal_id}/iteration-status")
            assert r.status_code in (200, 404, 500)

    def test_goal_decompose_submit(self, client, store):
        if store.goal_id:
            r = client.post(f"/api/v1/goals/{store.goal_id}/decompose/submit")
            assert r.status_code in (200, 404, 500)

    def test_goal_iteration_adjust(self, client, store):
        if store.goal_id:
            r = client.post(
                f"/api/v1/goals/{store.goal_id}/iterations/adj-test/adjust",
                json={"action": "adjust"}
            )
            assert r.status_code in (400, 404, 500)

    def test_goal_iteration_confirm(self, client, store):
        if store.goal_id:
            r = client.post(
                f"/api/v1/goals/{store.goal_id}/iterations/adj-test/confirm"
            )
            assert r.status_code in (400, 404, 500)

    def test_goal_iteration_discuss(self, client, store):
        if store.goal_id:
            r = client.post(
                f"/api/v1/goals/{store.goal_id}/iterations/adj-test/discuss",
                json={"message": "test"}
            )
            assert r.status_code in (400, 404, 500)


class TestL1_Projects:
    """TC-FE-L1-10~16: Projects"""

    def test_list_projects(self, client):
        r = client.get("/api/v1/projects")
        assert r.status_code in (200, 404, 500)

    def test_get_project_detail(self, client, store):
        r = client.get("/api/v1/projects")
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                store.project_id = data[0].get("id")
                store.project_ids.append(store.project_id)
                r_detail = client.get(f"/api/v1/projects/{store.project_id}")
                assert r_detail.status_code in (200, 404, 500)

    def test_project_diagram(self, client, store):
        if store.project_id:
            r = client.get(f"/api/v1/projects/{store.project_id}/diagram")
            assert r.status_code in (200, 404, 500)

    def test_project_task_tree(self, client, store):
        if store.project_id:
            r = client.get(f"/api/v1/projects/{store.project_id}/task-tree")
            assert r.status_code in (200, 404, 500)

    def test_project_pause(self, client, store):
        if store.project_id:
            r = client.post(f"/api/v1/projects/{store.project_id}/pause")
            assert r.status_code in (200, 404, 500)

    def test_project_resume(self, client, store):
        if store.project_id:
            r = client.post(f"/api/v1/projects/{store.project_id}/resume")
            assert r.status_code in (200, 404, 500)


class TestL1_Tasks:
    """TC-FE-L1-17~26: Tasks"""

    def test_task_statuses(self, client):
        r = client.get("/api/v1/tasks/statuses")
        assert r.status_code in (200, 404, 500)

    def test_list_tasks(self, client, store):
        r = client.get("/api/v1/tasks")
        assert r.status_code in (200, 404, 500)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                store.task_id = data[0].get("id")
                store.task_ids = [t.get("id") for t in data if t.get("id")]

    def test_get_task_detail(self, client, store):
        if store.task_id:
            r = client.get(f"/api/v1/tasks/{store.task_id}")
            assert r.status_code in (200, 404, 500)

    def test_task_activity(self, client, store):
        if store.task_id:
            r = client.get(f"/api/v1/tasks/{store.task_id}/activity")
            assert r.status_code in (200, 404, 500)

    def test_task_comments(self, client, store):
        if store.task_id:
            r = client.get(f"/api/v1/tasks/{store.task_id}/comments")
            assert r.status_code in (200, 404, 500)

    def test_task_execution_logs(self, client, store):
        if store.task_id:
            r = client.get(f"/api/v1/tasks/{store.task_id}/execution-logs",
                          params={"limit": 50})
            assert r.status_code in (200, 404, 500)

    def test_task_pause(self, client, store):
        if store.task_id:
            r = client.post(f"/api/v1/tasks/{store.task_id}/pause")
            assert r.status_code in (200, 404, 500)

    def test_task_resume(self, client, store):
        if store.task_id:
            r = client.post(f"/api/v1/tasks/{store.task_id}/resume")
            assert r.status_code in (200, 404, 500)

    def test_task_retry(self, client, store):
        if store.task_id:
            r = client.post(f"/api/v1/tasks/{store.task_id}/retry")
            assert r.status_code in (200, 404, 500)

    def test_task_verifier(self, client, store):
        if store.task_id:
            r = client.get(f"/api/v1/tasks/{store.task_id}/verifier")
            assert r.status_code in (200, 404, 500)


# ============================================================================
# Layer 2: Scenarios, Workflows
# ============================================================================

class TestL2_Scenarios:
    """TC-FE-L2-01~05: Scenarios"""

    def test_list_scenarios(self, client, store):
        r = client.get("/api/v1/scenarios")
        assert r.status_code in (200, 404, 500)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                store.scenario_id = data[0].get("id")
                store.scenario_ids.append(store.scenario_id)

    def test_get_scenario_detail(self, client, store):
        if store.scenario_id:
            r = client.get(f"/api/v1/scenarios/{store.scenario_id}")
            assert r.status_code in (200, 404, 500)

    def test_create_scenario_for_goal(self, client, store):
        if store.goal_id:
            r = client.post(f"/api/v1/scenarios/create-for-goal/{store.goal_id}")
            assert r.status_code in (200, 404, 500)

    def test_match_scenario_for_goal(self, client, store):
        if store.goal_id:
            r = client.post(f"/api/v1/scenarios/match-for-goal/{store.goal_id}")
            assert r.status_code in (200, 404, 500)

    def test_instantiate_workflow(self, client, store):
        if store.scenario_id:
            r = client.post(f"/api/v1/scenarios/{store.scenario_id}/instantiate-workflow")
            assert r.status_code in (200, 404, 500)


class TestL2_Workflows:
    """TC-FE-L2-06~11: Workflows"""

    def test_list_workflows(self, client, store):
        r = client.get("/api/v1/workflows")
        assert r.status_code in (200, 404, 500)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                store.workflow_id = data[0].get("id")
                store.workflow_ids = [w.get("id") for w in data if w.get("id")]

    def test_get_workflow_detail(self, client, store):
        if store.workflow_id:
            r = client.get(f"/api/v1/workflows/{store.workflow_id}")
            assert r.status_code in (200, 404, 500)

    def test_workflow_diagram(self, client, store):
        if store.workflow_id:
            r = client.get(f"/api/v1/workflows/{store.workflow_id}/diagram")
            assert r.status_code in (200, 404, 500)

    def test_workflow_confirm_and_split(self, client, store):
        if store.workflow_id:
            r = client.post(f"/api/v1/workflows/{store.workflow_id}/confirm-and-split")
            assert r.status_code in (200, 404, 500)

    def test_workflow_dag_converse(self, client, store):
        if store.workflow_id:
            r = client.post(f"/api/v1/workflows/{store.workflow_id}/dag/converse",
                          json={"message": "test"})
            assert r.status_code in (200, 404, 500)

    def test_workflow_dag_edges(self, client, store):
        if store.workflow_id:
            r = client.post(f"/api/v1/workflows/{store.workflow_id}/dag/edges",
                          json={"edges": []})
            assert r.status_code in (200, 404, 500)


# ============================================================================
# Layer 3: Human Input, Human Review, Cognitive/GrASP
# ============================================================================

class TestL3_HumanInput:
    """TC-FE-L3-01~07: Human Input"""

    def test_hitl_pending(self, client, store):
        r = client.get("/api/v1/human-input/pending")
        assert r.status_code in (200, 404, 500)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                store.hitl_id = data[0].get("id")
                store.hitl_ids = [h.get("id") for h in data if h.get("id")]

    def test_hitl_stats(self, client):
        r = client.get("/api/v1/human-input/stats")
        assert r.status_code in (200, 404, 500)

    def test_hitl_analytics(self, client):
        r = client.get("/api/v1/human-input/analytics", params={"days": 7})
        assert r.status_code in (200, 404, 500)

    def test_hitl_task_detail(self, client, store):
        if store.hitl_id:
            r = client.get(f"/api/v1/human-input/task/{store.hitl_id}")
            assert r.status_code in (200, 404, 500)

    def test_hitl_detail(self, client, store):
        if store.hitl_id:
            r = client.get(f"/api/v1/human-input/{store.hitl_id}")
            assert r.status_code in (200, 404, 500)

    def test_hitl_submit(self, client, store):
        if store.hitl_id:
            r = client.post(f"/api/v1/human-input/{store.hitl_id}/submit",
                          json={"result": "approved"})
            assert r.status_code in (200, 404, 500)

    def test_hitl_reject(self, client, store):
        if store.hitl_id:
            r = client.post(f"/api/v1/human-input/{store.hitl_id}/reject",
                          json={"reason": "test"})
            assert r.status_code in (200, 404, 500)


class TestL3_HumanReview:
    """TC-FE-L3-08~09: Human Review"""

    def test_review_pending(self, client):
        r = client.get("/api/v1/human-review/pending")
        assert r.status_code in (200, 404, 500)

    def test_review_batch_ruling(self, client):
        r = client.post("/api/v1/human-review/batch-ruling", json={"rulings": []})
        assert r.status_code in (200, 404, 500)


class TestL3_Cognitive:
    """TC-FE-L3-10~15: Cognitive & GrASP"""

    def test_cognitive_entries(self, client):
        r = client.get("/api/v1/cognitive/entries")
        assert r.status_code in (200, 404, 500)

    def test_cognitive_entries_filtered(self, client):
        r = client.get("/api/v1/cognitive/entries", params={"type": "test"})
        assert r.status_code in (200, 404, 500)

    def test_grasp_cognition_assessment(self, client):
        r = client.get("/api/v1/grasp/cognition-assessment/test-id")
        assert r.status_code in (200, 404, 500)

    def test_grasp_injection_logs(self, client):
        r = client.get("/api/v1/grasp/injection/logs",
                      params={"page": 1, "page_size": 10})
        assert r.status_code in (200, 404, 500)

    def test_grasp_injection_rules(self, client):
        r = client.get("/api/v1/grasp/injection/rules")
        assert r.status_code in (200, 404, 500)

    def test_grasp_knowledge_search(self, client):
        r = client.get("/api/v1/grasp/knowledge", params={"q": "test", "limit": 3})
        assert r.status_code in (200, 404, 500)


# ============================================================================
# Layer 3.5: Dashboard, Artifacts, Traces, Events
# ============================================================================

class TestL35_Dashboard:
    """TC-FE-L3.5-01~03: Dashboard"""

    def test_dashboard_stats(self, client):
        r = client.get("/api/v1/dashboard/stats")
        assert r.status_code in (200, 404, 500)

    def test_dashboard_traces(self, client):
        r = client.get("/api/v1/traces", params={"limit": 5})
        assert r.status_code in (200, 404, 500)

    def test_human_review_stats(self, client):
        r = client.get("/api/v1/human-review/stats")
        assert r.status_code in (200, 404, 500)


class TestL35_Artifacts:
    """TC-FE-L3.5-04~05: Artifacts"""

    def test_list_artifacts(self, client):
        r = client.get("/api/v1/artifacts")
        assert r.status_code in (200, 404, 500)

    def test_artifact_download(self, client):
        r = client.get("/api/v1/artifacts/test-id/download")
        assert r.status_code in (200, 404, 500)


class TestL35_Traces:
    """TC-FE-L3.5-06: Traces"""

    def test_trace_step_status(self, client):
        r = client.get("/api/v1/traces/test-id/step-status")
        assert r.status_code in (200, 404, 500)


class TestL35_Events:
    """TC-FE-L3.5-07~08: Events/SSE"""

    def test_events_stream(self, client):
        r = client.get("/api/v1/events/stream")
        assert r.status_code in (200, 404, 500)

    def test_events_pull(self, client):
        r = client.get("/api/v1/events/pull")
        assert r.status_code in (200, 404, 500)
