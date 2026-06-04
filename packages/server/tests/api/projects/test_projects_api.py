"""
Project API 单元测试
测试 Project CRUD API 端点
"""

import sys
import os

# os.chdir removed - using dynamic path resolution
sys.path.insert(0, '.')

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from models.base import Base
from models.goal import Goal
from models.project import Project
from reins.api.projects import router
from reins.common.database import get_db
from fastapi import FastAPI


# 创建测试数据库
TEST_DB_PATH = "data/test_projects.db"
engine = create_engine(f"sqlite:///{TEST_DB_PATH}", connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def setup_db():
    Base.metadata.create_all(bind=engine)

    db = TestSessionLocal()
    test_goal = Goal(
        id="goal-test-001",
        title="Test Goal",
        description="Test Goal Description",
        status="draft"
    )
    db.add(test_goal)
    db.commit()
    db.close()

    yield

    db = TestSessionLocal()
    db.execute(text("DELETE FROM project_members"))
    db.execute(text("DELETE FROM projects"))
    db.execute(text("DELETE FROM goals"))
    db.commit()
    db.close()


@pytest.fixture(scope="function")
def client(setup_db):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


BASE = "/api/v1/projects"


class TestProjectCreate:
    def test_create_project_basic(self, client):
        response = client.post(f"{BASE}/", json={
            "name": "Test Project",
            "description": "Test Description"
        })
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["description"] == "Test Description"
        assert data["status"] == "active"
        assert data["priority"] == "medium"
        assert "id" in data

    def test_create_project_with_goal(self, client):
        response = client.post(f"{BASE}/", json={
            "name": "Project with Goal",
            "description": "Linked to goal",
            "goal_id": "goal-test-001"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["goal_id"] == "goal-test-001"

    def test_create_project_with_all_fields(self, client):
        response = client.post(f"{BASE}/", json={
            "name": "Full Project",
            "description": "All fields",
            "status": "active",
            "priority": "high",
            "assignee": "agent-001",
            "due_date": "2026-12-31T23:59:59"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "active"
        assert data["priority"] == "high"
        assert data["assignee"] == "agent-001"

    def test_create_project_missing_name(self, client):
        response = client.post(f"{BASE}/", json={"description": "No name"})
        assert response.status_code == 422


class TestProjectRead:
    def test_list_projects_empty(self, client):
        response = client.get(f"{BASE}/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_projects_with_data(self, client):
        client.post(f"{BASE}/", json={"name": "Project 1"})
        client.post(f"{BASE}/", json={"name": "Project 2"})
        response = client.get(f"{BASE}/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_projects_filter_by_goal(self, client):
        client.post(f"{BASE}/", json={"name": "Project A", "goal_id": "goal-test-001"})
        client.post(f"{BASE}/", json={"name": "Project B"})
        response = client.get(f"{BASE}/", params={"goal_id": "goal-test-001"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Project A"

    def test_list_projects_filter_by_status(self, client):
        client.post(f"{BASE}/", json={"name": "Active Project", "status": "active"})
        client.post(f"{BASE}/", json={"name": "Archived Project", "status": "archived"})
        response = client.get(f"{BASE}/", params={"status": "active"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "active"

    def test_get_project(self, client):
        create_resp = client.post(f"{BASE}/", json={"name": "Get Test", "description": "Test get"})
        project_id = create_resp.json()["id"]
        response = client.get(f"{BASE}/{project_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test"

    def test_get_project_not_found(self, client):
        response = client.get(f"{BASE}/99999")
        assert response.status_code == 404


class TestProjectUpdate:
    def test_update_project(self, client):
        create_resp = client.post(f"{BASE}/", json={"name": "Original Name", "description": "Original"})
        project_id = create_resp.json()["id"]
        response = client.put(f"{BASE}/{project_id}", json={"name": "Updated Name", "description": "Updated"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated"

    def test_update_project_partial(self, client):
        create_resp = client.post(f"{BASE}/", json={"name": "Partial Test", "priority": "low"})
        project_id = create_resp.json()["id"]
        response = client.put(f"{BASE}/{project_id}", json={"priority": "high"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Partial Test"
        assert data["priority"] == "high"

    def test_update_project_not_found(self, client):
        response = client.put(f"{BASE}/99999", json={"name": "Test"})
        assert response.status_code == 404


class TestProjectDelete:
    def test_delete_project(self, client):
        create_resp = client.post(f"{BASE}/", json={"name": "Delete Test"})
        project_id = create_resp.json()["id"]
        response = client.delete(f"{BASE}/{project_id}")
        assert response.status_code == 204
        get_resp = client.get(f"{BASE}/{project_id}")
        assert get_resp.status_code == 404

    def test_delete_project_not_found(self, client):
        response = client.delete(f"{BASE}/99999")
        assert response.status_code == 404


class TestProjectFilters:
    def test_filter_by_priority(self, client):
        client.post(f"{BASE}/", json={"name": "P0", "priority": "critical"})
        client.post(f"{BASE}/", json={"name": "P1", "priority": "high"})
        client.post(f"{BASE}/", json={"name": "P2", "priority": "medium"})
        response = client.get(f"{BASE}/", params={"priority": "high"})
        data = response.json()
        assert len(data) == 1
        assert data[0]["priority"] == "high"

    def test_filter_by_assignee(self, client):
        client.post(f"{BASE}/", json={"name": "A1", "assignee": "agent-001"})
        client.post(f"{BASE}/", json={"name": "A2", "assignee": "agent-002"})
        response = client.get(f"{BASE}/", params={"assignee": "agent-001"})
        data = response.json()
        assert len(data) == 1
        assert data[0]["assignee"] == "agent-001"

    def test_multiple_filters(self, client):
        client.post(f"{BASE}/", json={
            "name": "Complex", "status": "active",
            "priority": "high", "assignee": "agent-001"
        })
        client.post(f"{BASE}/", json={
            "name": "Complex2", "status": "active",
            "priority": "high", "assignee": "agent-002"
        })
        client.post(f"{BASE}/", json={
            "name": "Different", "status": "active",
            "priority": "low", "assignee": "agent-001"
        })
        response = client.get(f"{BASE}/", params={
            "status": "active",
            "priority": "high",
            "assignee": "agent-001"
        })
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Complex"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
