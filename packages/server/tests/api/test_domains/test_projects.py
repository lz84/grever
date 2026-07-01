"""
Projects domain tests - All /api/v1/projects endpoints.

Tests cover: CRUD, status management, auto-assign, verifier, diagram, task-tree
"""
import pytest
from fastapi.testclient import TestClient
from .conftest import SharedData, gen_id


class TestProjectsList:
    """GET /api/v1/projects endpoints."""

    def test_list_projects(self, client: TestClient, ensure_baseline):
        resp = client.get("/api/v1/projects")
        assert resp.status_code != 500, f"500 on GET /api/v1/projects: {resp.text[:200]}"
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code}"
        data = resp.json()
        assert "projects" in data, "Response should contain 'projects' key"
        assert isinstance(data["projects"], list), "'projects' should be a list"

    def test_list_projects_trailing_slash(self, client: TestClient):
        resp = client.get("/api/v1/projects/")
        assert resp.status_code != 500

    def test_projects_count(self, client: TestClient):
        resp = client.get("/api/v1/projects/count")
        assert resp.status_code != 500

    def test_projects_debug_filter(self, client: TestClient):
        resp = client.get("/api/v1/projects/debug-filter")
        assert resp.status_code != 500


class TestProjectsCRUD:
    """Project CRUD operations."""

    def test_create_project(self, client: TestClient, shared_data: SharedData):
        resp = client.post("/api/v1/projects/", json={
            "name": gen_id("project"),
            "goal_id": gen_id("goal"),
            "description": "Test project"
        })
        assert resp.status_code != 500, f"500 on POST /api/v1/projects/: {resp.text[:200]}"
        if resp.status_code in (200, 201):
            data = resp.json()
            pid = data.get("id")
            if pid:
                shared_data.project_id = pid
                shared_data.project_ids.append(pid)

    def test_get_project(self, client: TestClient, shared_data: SharedData):
        if not shared_data.project_id:
            pytest.skip("No project created")
        resp = client.get(f"/api/v1/projects/{shared_data.project_id}")
        assert resp.status_code != 500

    def test_get_project_diagram(self, client: TestClient, shared_data: SharedData):
        if not shared_data.project_id:
            pytest.skip("No project created")
        resp = client.get(f"/api/v1/projects/{shared_data.project_id}/diagram")
        assert resp.status_code != 500

    def test_get_project_task_tree(self, client: TestClient, shared_data: SharedData):
        if not shared_data.project_id:
            pytest.skip("No project created")
        resp = client.get(f"/api/v1/projects/{shared_data.project_id}/task-tree")
        assert resp.status_code != 500

    def test_update_project(self, client: TestClient, shared_data: SharedData):
        if not shared_data.project_id:
            pytest.skip("No project created")
        resp = client.patch(
            f"/api/v1/projects/{shared_data.project_id}",
            json={"name": gen_id("project-updated")}
        )
        assert resp.status_code != 500

    def test_update_project_status(self, client: TestClient, shared_data: SharedData):
        if not shared_data.project_id:
            pytest.skip("No project created")
        resp = client.patch(
            f"/api/v1/projects/{shared_data.project_id}/status",
            json={"status": "active"}
        )
        assert resp.status_code != 500

    def test_delete_project(self, client: TestClient, shared_data: SharedData):
        if not shared_data.project_id:
            pytest.skip("No project created")
        resp = client.delete(f"/api/v1/projects/{shared_data.project_id}")
        assert resp.status_code != 500


class TestProjectOperations:
    """Project lifecycle operations."""

    def test_project_auto_assign(self, client: TestClient, shared_data: SharedData):
        if not shared_data.project_id:
            pytest.skip("No project created")
        resp = client.post(
            f"/api/v1/projects/{shared_data.project_id}/auto-assign", json={})
        assert resp.status_code != 500

    def test_project_pause(self, client: TestClient, shared_data: SharedData):
        if not shared_data.project_id:
            pytest.skip("No project created")
        resp = client.post(
            f"/api/v1/projects/{shared_data.project_id}/pause", json={})
        assert resp.status_code != 500

    def test_project_resume(self, client: TestClient, shared_data: SharedData):
        if not shared_data.project_id:
            pytest.skip("No project created")
        resp = client.post(
            f"/api/v1/projects/{shared_data.project_id}/resume", json={})
        assert resp.status_code != 500

    def test_project_verifier(self, client: TestClient, shared_data: SharedData):
        if not shared_data.project_id:
            pytest.skip("No project created")
        resp = client.post(
            f"/api/v1/projects/{shared_data.project_id}/verifier",
            json={"verifier_id": gen_id("agent")}
        )
        assert resp.status_code != 500

    def test_create_project_with_deps(self, client: TestClient):
        resp = client.post("/api/v1/projects/with-deps", json={
            "name": gen_id("project-deps"),
            "depends_on": []
        })
        assert resp.status_code != 500
