"""
Goals domain tests - All /api/v1/goals endpoints.

Layer: Core (depends on agents existing)
"""
import pytest
from fastapi.testclient import TestClient
from .conftest import SharedData, gen_id, now_ts


class TestGoalsList:
    """GET /api/v1/goals - List goals."""

    def test_list_goals_ok(self, client: TestClient, ensure_baseline):
        resp = client.get("/api/v1/goals")
        assert resp.status_code != 500, f"500 on GET /api/v1/goals: {resp.text[:300]}"
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code}"
        data = resp.json()
        assert isinstance(data, dict), f"Expected dict response, got {type(data).__name__}"
        assert "goals" in data, "Response should contain 'goals' key"
        assert isinstance(data["goals"], list), "'goals' should be a list"

    def test_list_goals_with_trailing_slash(self, client: TestClient):
        resp = client.get("/api/v1/goals/")
        assert resp.status_code != 500

    def test_list_active_goals(self, client: TestClient):
        resp = client.get("/api/v1/goals/active")
        assert resp.status_code != 500


class TestGoalsCRUD:
    """Goal CRUD operations."""

    def test_create_goal(self, client: TestClient, shared_data: SharedData):
        resp = client.post("/api/v1/goals/", json={
            "name": gen_id("goal"),
            "description": "Test goal for regression",
            "priority": "medium"
        })
        assert resp.status_code != 500, f"500 on POST /api/v1/goals/: {resp.text[:300]}"
        if resp.status_code == 200:
            data = resp.json()
            shared_data.goal_id = data.get("id")
            if shared_data.goal_id:
                shared_data.goal_ids.append(shared_data.goal_id)
                assert shared_data.goal_id is not None

    def test_get_goal(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.get(f"/api/v1/goals/{shared_data.goal_id}")
        assert resp.status_code != 500, f"500 on GET goal: {resp.text[:300]}"

    def test_get_nonexistent_goal(self, client: TestClient):
        resp = client.get(f"/api/v1/goals/{gen_id('nonexistent')}")
        # 404 is expected for nonexistent goal
        assert resp.status_code in (404, 200)

    def test_update_goal(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.put(f"/api/v1/goals/{shared_data.goal_id}", json={
            "name": gen_id("goal-updated"),
            "description": "Updated test goal"
        })
        assert resp.status_code != 500, f"500 on PUT goal: {resp.text[:300]}"

    def test_delete_goal(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        # Note: This may fail if there are dependent projects/tasks
        resp = client.delete(f"/api/v1/goals/{shared_data.goal_id}")
        assert resp.status_code != 500, f"500 on DELETE goal: {resp.text[:300]}"


class TestGoalOperations:
    """Goal lifecycle operations."""

    def test_goal_constraints(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.get(f"/api/v1/goals/{shared_data.goal_id}/constraints")
        assert resp.status_code != 500

    def test_goal_iteration_status(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.get(f"/api/v1/goals/{shared_data.goal_id}/iteration-status")
        assert resp.status_code != 500

    def test_goal_tree(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.get(f"/api/v1/goals/{shared_data.goal_id}/tree")
        assert resp.status_code != 500

    def test_goal_iterations(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.get(f"/api/v1/goals/{shared_data.goal_id}/iterations")
        assert resp.status_code != 500

    def test_goal_activate(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.post(f"/api/v1/goals/{shared_data.goal_id}/activate", json={})
        assert resp.status_code != 500

    def test_goal_status_update(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.patch(
            f"/api/v1/goals/{shared_data.goal_id}/status",
            json={"status": "active"}
        )
        assert resp.status_code != 500

    def test_goal_auto_assign(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.post(f"/api/v1/goals/{shared_data.goal_id}/auto-assign", json={})
        assert resp.status_code != 500

    def test_goal_assign_tasks(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.post(f"/api/v1/goals/{shared_data.goal_id}/assign-tasks", json={})
        assert resp.status_code != 500

    def test_goal_pause(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.post(f"/api/v1/goals/{shared_data.goal_id}/pause", json={})
        assert resp.status_code != 500

    def test_goal_resume(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.post(f"/api/v1/goals/{shared_data.goal_id}/resume", json={})
        assert resp.status_code != 500

    def test_goal_verifier(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.post(
            f"/api/v1/goals/{shared_data.goal_id}/verifier",
            json={"verifier_id": gen_id("agent")}
        )
        assert resp.status_code != 500


class TestGoalDecomposition:
    """Goal decomposition endpoints."""

    def test_goal_auto_decompose(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.post(f"/api/v1/goals/{shared_data.goal_id}/auto-decompose", json={})
        assert resp.status_code != 500

    def test_goal_auto_decompose_preview(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.post(
            f"/api/v1/goals/{shared_data.goal_id}/auto-decompose/preview", json={})
        assert resp.status_code != 500

    def test_goal_decompose_submit(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.post(
            f"/api/v1/goals/{shared_data.goal_id}/decompose/submit",
            json={"answers": []}
        )
        assert resp.status_code != 500

    def test_goal_project_assign_tasks(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.post(
            f"/api/v1/goals/projects/{shared_data.goal_id}/assign-tasks", json={})
        assert resp.status_code != 500


class TestGoalIteration:
    """Goal iteration endpoints."""

    def test_goal_iterate(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.post(f"/api/v1/goals/{shared_data.goal_id}/iterate", json={})
        assert resp.status_code != 500

    def test_goal_start_iteration(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.post(f"/api/v1/goals/{shared_data.goal_id}/start-iteration", json={})
        assert resp.status_code != 500

    def test_goal_pause_iteration(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.post(
            f"/api/v1/goals/{shared_data.goal_id}/pause-iteration", json={})
        assert resp.status_code != 500

    def test_goal_converge_iteration(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.post(
            f"/api/v1/goals/{shared_data.goal_id}/converge-iteration", json={})
        assert resp.status_code != 500

    def test_goal_mode(self, client: TestClient, shared_data: SharedData):
        if not shared_data.goal_id:
            pytest.skip("No goal created yet")
        resp = client.post(
            f"/api/v1/goals/{shared_data.goal_id}/mode", json={"mode": "manual"})
        assert resp.status_code != 500
