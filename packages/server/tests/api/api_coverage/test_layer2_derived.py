"""
第 2 层：派生资源测试

依赖第 1 层：至少 1 个 active Goal + Tasks。
Scenarios, Workflows, Solutions。

对应测试用例：TC-L3-W-010~024, TC-L3-SC-020~027, TC-L3-SL-01~05
"""
import pytest
from conftest import gen_id, default_capability_tags


class TestLayer2_Workflows:
    """TC-L3-W-010~024: Workflow CRUD + DAG"""

    def test_01_list_workflows(self, client, shared_data):
        """TC-L3-W-010: 获取 Workflow 列表"""
        resp = client.get("/api/v1/workflows")
        assert resp.status_code == 200

    def test_02_get_workflow(self, client, shared_data):
        """TC-L3-W-011: 获取单个 Workflow"""
        resp = client.get("/api/v1/workflows")
        data = resp.json()
        workflows = data if isinstance(data, list) else data.get("workflows", [])
        if workflows:
            wf_id = workflows[0].get("id")
            shared_data.workflow_id = wf_id
            resp = client.get(f"/api/v1/workflows/{wf_id}")
            assert resp.status_code == 200

    def test_03_workflow_progress(self, client, shared_data):
        """TC-L3-W-013: 获取执行进度"""
        if not shared_data.workflow_id:
            pytest.skip("No workflow")
        resp = client.get(f"/api/v1/workflows/{shared_data.workflow_id}/progress")
        assert resp.status_code in (200, 404)

    def test_04_workflow_diagram(self, client, shared_data):
        """TC-L3-W-014: 获取流程图"""
        if not shared_data.workflow_id:
            pytest.skip("No workflow")
        resp = client.get(f"/api/v1/workflows/{shared_data.workflow_id}/diagram")
        assert resp.status_code in (200, 404)

    def test_05_workflow_conversation_history(self, client, shared_data):
        """TC-L3-W-024: 获取对话历史"""
        if not shared_data.workflow_id:
            pytest.skip("No workflow")
        resp = client.get(f"/api/v1/workflows/{shared_data.workflow_id}/dag/conversation/history")
        assert resp.status_code in (200, 404)


class TestLayer2_Scenarios:
    """TC-L3-SC-020~027: Scenarios 扩展"""

    def test_01_list_scenarios(self, client, shared_data):
        """TC-L3: GET /scenarios"""
        resp = client.get("/api/v1/scenarios")
        assert resp.status_code == 200
        data = resp.json()
        scenarios = data if isinstance(data, list) else data.get("scenarios", data.get("items", []))
        if scenarios:
            shared_data.scenario_id = scenarios[0].get("id")

    def test_02_get_scenario(self, client, shared_data):
        """TC-L3: GET /scenarios/{id}"""
        if not shared_data.scenario_id:
            pytest.skip("No scenario")
        resp = client.get(f"/api/v1/scenarios/{shared_data.scenario_id}")
        assert resp.status_code == 200

    def test_03_scenario_versions(self, client, shared_data):
        """TC-L3-SC-024: 获取场景版本历史"""
        if not shared_data.scenario_id:
            pytest.skip("No scenario")
        resp = client.get(f"/api/v1/scenarios/{shared_data.scenario_id}/versions")
        assert resp.status_code in (200, 404)

    def test_04_scenario_match_preview(self, client, shared_data):
        """TC-L3-SC-027: 匹配预览"""
        resp = client.post("/api/v1/scenarios/match-preview", json={
            "goal_id": shared_data.goal_id if shared_data.goal_id else gen_id("goal")
        })
        assert resp.status_code in (200, 400, 404, 422)

    def test_05_scenario_custom_create(self, client):
        """TC-L3-SC-020: 手动创建场景"""
        resp = client.post("/api/v1/scenarios/custom-create", json={
            "title": "Layer2 Test Scenario",
            "description": "API coverage test scenario",
        })
        assert resp.status_code in (200, 201, 400, 422)


class TestLayer2_Solutions:
    """TC-L3-SL-01~05: Solutions 方案体系"""

    def test_01_list_solutions(self, client, shared_data):
        """TC-L3-SL-01: 获取方案列表"""
        resp = client.get("/api/v1/solutions")
        assert resp.status_code == 200
        data = resp.json()
        solutions = data if isinstance(data, list) else data.get("solutions", data.get("items", []))
        if solutions:
            shared_data.solution_id = solutions[0].get("id")

    def test_02_get_solution(self, client, shared_data):
        """TC-L3-SL-02: 获取方案详情"""
        if not shared_data.solution_id:
            pytest.skip("No solution")
        resp = client.get(f"/api/v1/solutions/{shared_data.solution_id}")
        assert resp.status_code in (200, 404)

    def test_03_solutions_compare(self, client, shared_data):
        """TC-L3-SL-03: 对比方案"""
        resp = client.post("/api/v1/solutions/compare", json={
            "solution_a": "test-a",
            "solution_b": "test-b",
        })
        assert resp.status_code in (200, 400, 404)

    def test_04_solutions_trend(self, client):
        """TC-L3-SL: 方案趋势"""
        resp = client.get("/api/v1/solutions/trend")
        assert resp.status_code == 200
