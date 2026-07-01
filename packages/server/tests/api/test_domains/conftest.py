"""
Conftest for test_domains - shared fixtures for domain tests.

Each domain test class uses `ensure_baseline` fixture to guarantee minimal test data
(agent, goal, project, task, scenario) exists before running tests.
"""
import sys
import os
from pathlib import Path

_src = str(Path(__file__).parent.parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

import pytest
import uuid
import time
from fastapi.testclient import TestClient
from api.server import create_app


@pytest.fixture(scope="session")
def app():
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    return TestClient(app, raise_server_exceptions=False)


class SharedData:
    """Shared test data populated by ensure_baseline fixture."""
    agent_id = None
    agent_ids = []
    goal_id = None
    goal_ids = []
    project_id = None
    project_ids = []
    task_id = None
    task_ids = []
    workflow_id = None
    scenario_id = None
    scenario_ids = []
    solution_id = None
    solution_ids = []
    dispute_id = None
    cognition_id = None
    hitl_id = None
    pack_id = None
    skill_id = None
    artifact_id = None
    capsule_id = None
    gene_id = None
    role_id = None


@pytest.fixture(scope="session")
def shared_data():
    return SharedData()


def gen_id(prefix="test"):
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def now_ts():
    return int(time.time())


@pytest.fixture(scope="session")
def ensure_baseline(client, shared_data):
    """Auto-create minimal test data for all domain tests."""
    if not shared_data.agent_id:
        r = client.post("/api/v1/agents", json={
            "name": f"agent-{gen_id()[:8]}",
            "model": "gpt-4o", "platform_type": "openai"
        })
        if r.status_code in (200, 201):
            shared_data.agent_id = r.json().get("id")

    if not shared_data.goal_id:
        r = client.post("/api/v1/goals/", json={
            "title": f"goal-{gen_id()[:8]}",
            "description": "Baseline goal for domain tests"
        })
        if r.status_code in (200, 201):
            shared_data.goal_id = r.json().get("id")

    if not shared_data.project_id and shared_data.goal_id:
        r = client.post("/api/v1/projects/", json={
            "name": f"proj-{gen_id()[:8]}",
            "goal_id": shared_data.goal_id
        })
        if r.status_code in (200, 201):
            shared_data.project_id = r.json().get("id")

    if not shared_data.task_id and shared_data.project_id:
        r = client.post("/api/v1/tasks/", json={
            "title": f"task-{gen_id()[:8]}",
            "project_id": shared_data.project_id
        })
        if r.status_code in (200, 201):
            shared_data.task_id = r.json().get("id")

    if not shared_data.scenario_id:
        r = client.post("/api/v1/scenarios/", json={
            "name": f"scenario-{gen_id()[:8]}"
        })
        if r.status_code in (200, 201):
            shared_data.scenario_id = r.json().get("id")

    return shared_data
