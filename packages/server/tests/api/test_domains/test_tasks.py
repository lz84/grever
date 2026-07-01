"""
Tasks domain tests - All /api/v1/tasks endpoints.

Tests cover: CRUD, status management, lifecycle operations, attachments, comments, labels, HITL
"""
import pytest
from fastapi.testclient import TestClient
from .conftest import SharedData, gen_id


class TestTasksList:
    """GET /api/v1/tasks list endpoints."""

    def test_list_tasks(self, client: TestClient):
        resp = client.get("/api/v1/tasks")
        assert resp.status_code != 500, f"500 on GET /api/v1/tasks: {resp.text[:200]}"
        assert resp.status_code == 200, f"Unexpected status: {resp.status_code}"
        data = resp.json()
        assert "tasks" in data, "Response should contain 'tasks' key"
        assert isinstance(data["tasks"], list), "'tasks' should be a list"

    def test_list_tasks_trailing_slash(self, client: TestClient):
        resp = client.get("/api/v1/tasks/")
        assert resp.status_code != 500

    def test_tasks_count(self, client: TestClient):
        resp = client.get("/api/v1/tasks/count")
        assert resp.status_code != 500

    def test_tasks_statuses(self, client: TestClient):
        resp = client.get("/api/v1/tasks/statuses")
        assert resp.status_code != 500

    def test_tasks_labels_all(self, client: TestClient):
        resp = client.get("/api/v1/tasks/labels/all")
        assert resp.status_code != 500


class TestTasksCRUD:
    """Task CRUD operations."""

    def test_create_task(self, client: TestClient, shared_data: SharedData):
        resp = client.post("/api/v1/tasks/", json={
            "title": gen_id("task"),
            "project_id": gen_id("project"),
            "priority": "medium"
        })
        assert resp.status_code != 500, f"500 on POST /api/v1/tasks/: {resp.text[:200]}"
        if resp.status_code in (200, 201):
            data = resp.json()
            tid = data.get("id")
            if tid:
                shared_data.task_id = tid
                shared_data.task_ids.append(tid)

    def test_get_task(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.get(f"/api/v1/tasks/{shared_data.task_id}")
        assert resp.status_code != 500

    def test_get_task_context(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.get(f"/api/v1/tasks/{shared_data.task_id}/context")
        assert resp.status_code != 500

    def test_get_task_activity(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.get(f"/api/v1/tasks/{shared_data.task_id}/activity")
        assert resp.status_code != 500

    def test_get_task_parent(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.get(f"/api/v1/tasks/{shared_data.task_id}/parent")
        assert resp.status_code != 500

    def test_get_task_subtasks(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.get(f"/api/v1/tasks/{shared_data.task_id}/subtasks")
        assert resp.status_code != 500

    def test_get_task_execution_logs(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.get(f"/api/v1/tasks/{shared_data.task_id}/execution-logs")
        assert resp.status_code != 500

    def test_get_task_failure_log(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.get(f"/api/v1/tasks/{shared_data.task_id}/failure-log")
        assert resp.status_code != 500

    def test_get_task_verifications(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.get(f"/api/v1/tasks/{shared_data.task_id}/verifications")
        assert resp.status_code != 500

    def test_get_task_verifier(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.get(f"/api/v1/tasks/{shared_data.task_id}/verifier")
        assert resp.status_code != 500

    def test_update_task(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.put(
            f"/api/v1/tasks/{shared_data.task_id}",
            json={"title": gen_id("task-updated")}
        )
        assert resp.status_code != 500

    def test_update_task_status(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.patch(
            f"/api/v1/tasks/{shared_data.task_id}/status",
            json={"status": "done"}
        )
        assert resp.status_code != 500

    def test_update_task_depends_on(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.put(
            f"/api/v1/tasks/{shared_data.task_id}/depends_on",
            json={"depends_on": []}
        )
        assert resp.status_code != 500

    def test_batch_update_tasks(self, client: TestClient):
        resp = client.patch("/api/v1/tasks/batch", json={
            "task_ids": [],
            "updates": {}
        })
        assert resp.status_code != 500

    def test_delete_task(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.delete(f"/api/v1/tasks/{shared_data.task_id}")
        assert resp.status_code != 500


class TestTaskLifecycle:
    """Task lifecycle operations."""

    def test_task_assign(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/assign",
            json={"agent_id": gen_id("agent")}
        )
        assert resp.status_code != 500

    def test_task_verify(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/verify",
            json={"result": "pass"}
        )
        assert resp.status_code != 500

    def test_task_verifier_set(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/verifier",
            json={"verifier_id": gen_id("agent")}
        )
        assert resp.status_code != 500

    def test_task_review(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/review",
            json={"result": "pass"}
        )
        assert resp.status_code != 500

    def test_task_ruling(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/ruling",
            json={"ruling": "approve"}
        )
        assert resp.status_code != 500

    def test_task_progress(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/progress",
            json={"progress": 50}
        )
        assert resp.status_code != 500

    def test_task_pause(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/pause", json={})
        assert resp.status_code != 500

    def test_task_resume(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/resume", json={})
        assert resp.status_code != 500

    def test_task_block(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.patch(
            f"/api/v1/tasks/{shared_data.task_id}/block",
            json={"reason": "blocked by deps"}
        )
        assert resp.status_code != 500

    def test_task_unblock(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.patch(
            f"/api/v1/tasks/{shared_data.task_id}/unblock", json={})
        assert resp.status_code != 500

    def test_task_restart(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/restart", json={})
        assert resp.status_code != 500

    def test_task_retry(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/retry", json={})
        assert resp.status_code != 500

    def test_task_fail(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/fail",
            json={"reason": "test failure"}
        )
        assert resp.status_code != 500

    def test_task_terminate(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/terminate", json={})
        assert resp.status_code != 500

    def test_task_takeover(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/takeover",
            json={"agent_id": gen_id("agent")}
        )
        assert resp.status_code != 500


class TestTaskSubResources:
    """Task sub-resources: comments, labels, attachments, sub-issues, HITL."""

    def test_task_add_hitl(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/add-hitl",
            json={"type": "approval"}
        )
        assert resp.status_code != 500

    def test_task_comments_list(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.get(f"/api/v1/tasks/{shared_data.task_id}/comments")
        assert resp.status_code != 500

    def test_task_comment_create(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/comments",
            json={"content": "test comment"}
        )
        assert resp.status_code != 500

    def test_task_labels_list(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.get(f"/api/v1/tasks/{shared_data.task_id}/labels")
        assert resp.status_code != 500

    def test_task_label_create(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/labels",
            json={"label": "test-label"}
        )
        assert resp.status_code != 500

    def test_task_sub_issues_list(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.get(f"/api/v1/tasks/{shared_data.task_id}/sub-issues")
        assert resp.status_code != 500

    def test_task_sub_issue_create(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.post(
            f"/api/v1/tasks/{shared_data.task_id}/sub-issues",
            json={"title": gen_id("sub-issue")}
        )
        assert resp.status_code != 500

    def test_task_attachments_list(self, client: TestClient, shared_data: SharedData):
        if not shared_data.task_id:
            pytest.skip("No task created")
        resp = client.get(f"/api/v1/tasks/{shared_data.task_id}/attachments")
        assert resp.status_code != 500
