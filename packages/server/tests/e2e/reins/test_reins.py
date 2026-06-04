"""
测试 Reins 服务
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from api.server import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as tc:
        yield tc


def test_health_check(client):
    """测试健康检查"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_goals_crud(client):
    """测试目标管理"""
    # 创建目标
    response = client.post("/api/v1/goals", json={
        "title": "测试目标",
        "description": "这是一个测试目标"
    })
    assert response.status_code == 200
    goal_id = response.json()["id"]

    # 获取目标
    response = client.get(f"/api/v1/goals/{str(goal_id)}")
    assert response.status_code == 200
    assert response.json()["title"] == "测试目标"

    # 列出目标
    response = client.get("/api/v1/goals")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_projects_crud(client):
    """测试项目管理"""
    response = client.post("/api/v1/projects", json={
        "name": "测试项目",
        "description": "这是一个测试项目"
    })
    assert response.status_code == 200
    project_id = str(response.json()["id"])

    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "测试项目"

    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_tasks_crud(client):
    """测试任务管理"""
    response = client.post("/api/v1/tasks", json={
        "title": "测试任务",
        "description": "这是一个测试任务"
    })
    assert response.status_code == 200
    task_id = str(response.json()["id"])

    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "测试任务"

    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_agents_crud(client):
    """测试 Agent 注册"""
    response = client.post("/api/v1/agents", json={
        "agent_id": "test-agent-1",
        "name": "测试 Agent",
        "capabilities": ["task_execution", "data_analysis"]
    })
    assert response.status_code == 200

    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_disputes_crud(client):
    """测试争议管理"""
    response = client.post("/api/v1/disputes", json={
        "dispute_type": "resource_conflict",
        "description": "这是一个测试争议"
    })
    assert response.status_code == 200
    dispute_id = response.json()["id"]

    response = client.get(f"/api/v1/disputes/{dispute_id}")
    assert response.status_code == 200
    assert response.json()["dispute_type"] == "resource_conflict"

    response = client.get("/api/v1/disputes")
    assert response.status_code == 200
    assert len(response.json()) > 0
