"""
Solutions domain tests - All /api/v1/solutions endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from .conftest import SharedData, gen_id


class TestSolutionsList:
    """GET /api/v1/solutions"""

    def test_list_solutions(self, client: TestClient):
        resp = client.get("/api/v1/solutions")
        assert resp.status_code != 500

    def test_get_solution(self, client: TestClient, shared_data: SharedData):
        if not shared_data.solution_id:
            pytest.skip("No solution created")
        resp = client.get(f"/api/v1/solutions/{shared_data.solution_id}")
        assert resp.status_code != 500

    def test_solutions_compare(self, client: TestClient):
        resp = client.get("/api/v1/solutions/compare")
        assert resp.status_code != 500

    def test_solutions_compare_multi(self, client: TestClient):
        resp = client.get("/api/v1/solutions/compare/multi")
        assert resp.status_code != 500

    def test_solutions_trend(self, client: TestClient):
        resp = client.get("/api/v1/solutions/trend")
        assert resp.status_code != 500


class TestSolutionsCRUD:
    """Solution CRUD operations."""

    def test_create_solution(self, client: TestClient, shared_data: SharedData):
        resp = client.post("/api/v1/solutions", json={
            "goal_id": gen_id("goal"),
            "content": "test solution"
        })
        assert resp.status_code != 500, f"500 on POST /api/v1/solutions: {resp.text[:200]}"
        if resp.status_code in (200, 201):
            data = resp.json()
            sid = data.get("id")
            if sid:
                shared_data.solution_id = sid
                shared_data.solution_ids.append(sid)

    def test_update_solution(self, client: TestClient, shared_data: SharedData):
        if not shared_data.solution_id:
            pytest.skip("No solution created")
        resp = client.put(
            f"/api/v1/solutions/{shared_data.solution_id}",
            json={"content": "updated solution"}
        )
        assert resp.status_code != 500

    def test_delete_solution(self, client: TestClient, shared_data: SharedData):
        if not shared_data.solution_id:
            pytest.skip("No solution created")
        resp = client.delete(f"/api/v1/solutions/{shared_data.solution_id}")
        assert resp.status_code != 500

    def test_solutions_compare_post(self, client: TestClient):
        resp = client.post("/api/v1/solutions/compare", json={
            "solution_ids": []
        })
        assert resp.status_code != 500
