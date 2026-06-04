"""
测试 Reins 服务
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from reins.main import main
from reins import ReinsServer
from reins.persistence.base import DatabaseConfig


def test_reins_server():
    """测试 Reins 服务器"""
    # 创建数据库配置
    db_config = DatabaseConfig(
        provider="sqlite",
        path=":memory:"
    )
    
    # 创建 Reins Server
    reins_server = ReinsServer(db_config=db_config)
    
    # 创建 FastAPI 应用
    from reins.api.server import create_app
    app = create_app()
    
    # 设置应用的 state
    app.state.reins_server = reins_server
    
    # 创建测试客户端
    client = TestClient(app)
    
    # 测试健康检查
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "reins"}
    
    # 测试目标管理
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
    
    # 测试项目管理
    # 创建项目
    response = client.post("/api/v1/projects", json={
        "name": "测试项目",
        "description": "这是一个测试项目"
    })
    assert response.status_code == 200
    project_id = str(response.json()["id"])
    
    # 获取项目
    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "测试项目"
    
    # 列出项目
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    assert len(response.json()) > 0
    
    # 测试任务管理
    # 创建任务
    response = client.post("/api/v1/tasks", json={
        "title": "测试任务",
        "description": "这是一个测试任务",
        "project_id": project_id
    })
    assert response.status_code == 200
    task_id = str(response.json()["id"])
    
    # 获取任务
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "测试任务"
    
    # 列出任务
    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    assert len(response.json()) > 0
    
    # 测试 Agent 注册
    # 注册 Agent
    response = client.post("/api/v1/agents", json={
        "agent_id": "test-agent-1",
        "name": "测试 Agent",
        "capabilities": ["task_execution", "data_analysis"]
    })
    assert response.status_code == 200
    
    # 获取已注册 Agent
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    assert len(response.json()) > 0
    
    # 测试争议管理
    # 发起争议
    response = client.post("/api/v1/disputes", json={
        "dispute_type": "resource_conflict",
        "description": "这是一个测试争议",
        "involved_agents": ["test-agent-1"],
        "related_task_id": task_id
    })
    assert response.status_code == 200
    dispute_id = response.json()["id"]
    
    # 获取争议
    response = client.get(f"/api/v1/disputes/{dispute_id}")
    assert response.status_code == 200
    assert response.json()["dispute_type"] == "resource_conflict"
    
    # 列出争议
    response = client.get("/api/v1/disputes")
    assert response.status_code == 200
    assert len(response.json()) > 0
    
    print("All tests passed successfully!")


if __name__ == "__main__":
    test_reins_server()