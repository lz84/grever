"""
Scenarios domain tests - All /api/v1/scenarios endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from .conftest import SharedData, gen_id


class TestScenariosList:
    """GET /api/v1/scenarios"""

    def test_list_scenarios(self, client: TestClient):
        resp = client.get("/api/v1/scenarios/")
        assert resp.status_code != 500

    def test_get_scenario(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.get(f"/api/v1/scenarios/{shared_data.scenario_id}")
        assert resp.status_code != 500

    def test_get_scenario_fullset(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.get(f"/api/v1/scenarios/{shared_data.scenario_id}/fullset")
        assert resp.status_code != 500

    def test_get_scenario_preview(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.get(f"/api/v1/scenarios/{shared_data.scenario_id}/preview")
        assert resp.status_code != 500

    def test_get_scenario_status(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.get(f"/api/v1/scenarios/{shared_data.scenario_id}/status")
        assert resp.status_code != 500

    def test_get_scenario_versions(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.get(f"/api/v1/scenarios/{shared_data.scenario_id}/versions")
        assert resp.status_code != 500


class TestScenariosCRUD:
    """Scenario CRUD operations."""

    def test_create_scenario(self, client: TestClient, shared_data: SharedData):
        resp = client.post("/api/v1/scenarios/", json={
            "name": gen_id("scenario"),
            "description": "Test scenario"
        })
        assert resp.status_code != 500, f"500 on POST /api/v1/scenarios/: {resp.text[:200]}"
        if resp.status_code in (200, 201):
            data = resp.json()
            sid = data.get("id")
            if sid:
                shared_data.scenario_id = sid
                shared_data.scenario_ids.append(sid)

    def test_update_scenario(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.put(
            f"/api/v1/scenarios/{shared_data.scenario_id}",
            json={"name": gen_id("scenario-updated")}
        )
        assert resp.status_code != 500

    def test_update_scenario_status(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.patch(
            f"/api/v1/scenarios/{shared_data.scenario_id}/status",
            json={"status": "active"}
        )
        assert resp.status_code != 500

    def test_delete_scenario(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.delete(f"/api/v1/scenarios/{shared_data.scenario_id}")
        assert resp.status_code != 500


class TestScenarioOperations:
    """Scenario sub-resource operations."""

    def test_scenario_feedback(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.post(
            f"/api/v1/scenarios/{shared_data.scenario_id}/feedback",
            json={"feedback": "test feedback"}
        )
        assert resp.status_code != 500

    def test_scenario_review(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.post(
            f"/api/v1/scenarios/{shared_data.scenario_id}/review", json={})
        assert resp.status_code != 500

    def test_scenario_instantiate_to_goal(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.post(
            f"/api/v1/scenarios/{shared_data.scenario_id}/instantiate-to-goal",
            json={"goal_id": gen_id("goal")}
        )
        assert resp.status_code != 500

    def test_scenario_create_project(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.post(
            f"/api/v1/scenarios/{shared_data.scenario_id}/projects",
            json={"name": gen_id("project")}
        )
        assert resp.status_code != 500

    def test_scenario_delete_project(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.delete(
            f"/api/v1/scenarios/{shared_data.scenario_id}/projects/{gen_id('project')}")
        assert resp.status_code != 500

    def test_scenario_update_project(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.put(
            f"/api/v1/scenarios/{shared_data.scenario_id}/projects/{gen_id('project')}",
            json={"name": "updated"}
        )
        assert resp.status_code != 500

    def test_scenario_create_task(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.post(
            f"/api/v1/scenarios/{shared_data.scenario_id}/tasks",
            json={"name": gen_id("task")}
        )
        assert resp.status_code != 500

    def test_scenario_delete_task(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.delete(
            f"/api/v1/scenarios/{shared_data.scenario_id}/tasks/{gen_id('task')}")
        assert resp.status_code != 500

    def test_scenario_update_task(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.put(
            f"/api/v1/scenarios/{shared_data.scenario_id}/tasks/{gen_id('task')}",
            json={"name": "updated"}
        )
        assert resp.status_code != 500

    def test_scenario_fullset_update(self, client: TestClient, shared_data: SharedData):
        if not shared_data.scenario_id:
            pytest.skip("No scenario created")
        resp = client.put(
            f"/api/v1/scenarios/{shared_data.scenario_id}/fullset",
            json={}
        )
        assert resp.status_code != 500

    def test_scenario_custom_create(self, client: TestClient):
        resp = client.post("/api/v1/scenarios/custom-create", json={})
        assert resp.status_code != 500
