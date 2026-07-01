"""
Workflows domain tests - All /api/v1/workflows endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from .conftest import SharedData, gen_id


class TestWorkflowsList:
    """GET /api/v1/workflows"""

    def test_list_workflows(self, client: TestClient):
        resp = client.get("/api/v1/workflows/")
        assert resp.status_code != 500

    def test_get_workflow_progress(self, client: TestClient, shared_data: SharedData):
        if not shared_data.workflow_id:
            pytest.skip("No workflow created")
        resp = client.get(f"/api/v1/workflows/{shared_data.workflow_id}/progress")
        assert resp.status_code != 500

    def test_get_workflow_dag_conversation_history(self, client: TestClient, shared_data: SharedData):
        if not shared_data.workflow_id:
            pytest.skip("No workflow created")
        resp = client.get(f"/api/v1/workflows/{shared_data.workflow_id}/dag/conversation/history")
        assert resp.status_code != 500


class TestWorkflowOperations:
    """Workflow lifecycle operations."""

    def test_workflow_activate(self, client: TestClient, shared_data: SharedData):
        if not shared_data.workflow_id:
            pytest.skip("No workflow created")
        resp = client.post(
            f"/api/v1/workflows/{shared_data.workflow_id}/activate", json={})
        assert resp.status_code != 500

    def test_workflow_dag_edit(self, client: TestClient, shared_data: SharedData):
        if not shared_data.workflow_id:
            pytest.skip("No workflow created")
        resp = client.patch(
            f"/api/v1/workflows/{shared_data.workflow_id}/dag", json={})
        assert resp.status_code != 500

    def test_workflow_dag_nodes_create(self, client: TestClient, shared_data: SharedData):
        if not shared_data.workflow_id:
            pytest.skip("No workflow created")
        resp = client.post(
            f"/api/v1/workflows/{shared_data.workflow_id}/dag/nodes", json={})
        assert resp.status_code != 500

    def test_workflow_dag_nodes_edit(self, client: TestClient, shared_data: SharedData):
        if not shared_data.workflow_id:
            pytest.skip("No workflow created")
        resp = client.patch(
            f"/api/v1/workflows/{shared_data.workflow_id}/dag/nodes/node1", json={})
        assert resp.status_code != 500

    def test_workflow_dag_nodes_delete(self, client: TestClient, shared_data: SharedData):
        if not shared_data.workflow_id:
            pytest.skip("No workflow created")
        resp = client.delete(
            f"/api/v1/workflows/{shared_data.workflow_id}/dag/nodes/node1")
        assert resp.status_code != 500

    def test_workflow_dag_edges_create(self, client: TestClient, shared_data: SharedData):
        if not shared_data.workflow_id:
            pytest.skip("No workflow created")
        resp = client.post(
            f"/api/v1/workflows/{shared_data.workflow_id}/dag/edges", json={})
        assert resp.status_code != 500

    def test_workflow_dag_edges_delete(self, client: TestClient, shared_data: SharedData):
        if not shared_data.workflow_id:
            pytest.skip("No workflow created")
        resp = client.delete(
            f"/api/v1/workflows/{shared_data.workflow_id}/dag/edges/src/tgt")
        assert resp.status_code != 500

    def test_workflow_dag_reorder(self, client: TestClient, shared_data: SharedData):
        if not shared_data.workflow_id:
            pytest.skip("No workflow created")
        resp = client.post(
            f"/api/v1/workflows/{shared_data.workflow_id}/dag/reorder", json={})
        assert resp.status_code != 500

    def test_workflow_dag_converse(self, client: TestClient, shared_data: SharedData):
        if not shared_data.workflow_id:
            pytest.skip("No workflow created")
        resp = client.post(
            f"/api/v1/workflows/{shared_data.workflow_id}/dag/converse",
            json={"message": "test"}
        )
        assert resp.status_code != 500

    def test_workflow_dag_conversation_reset(self, client: TestClient, shared_data: SharedData):
        if not shared_data.workflow_id:
            pytest.skip("No workflow created")
        resp = client.post(
            f"/api/v1/workflows/{shared_data.workflow_id}/dag/conversation/reset", json={})
        assert resp.status_code != 500
