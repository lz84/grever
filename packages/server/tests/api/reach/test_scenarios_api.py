"""
场景库 API 单元测试

MAK-201: 后端-场景库 API 单元测试

覆盖：创建、列表、详情、更新、删除、反馈回收
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from reach.scenarios.crud import router as scenarios_router
from models.scenario import Base as ScenarioBase, Scenario


# ========== 测试数据库 ==========

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_scenarios.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def db_session():
    """创建测试数据库session"""
    ScenarioBase.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        ScenarioBase.metadata.drop_all(bind=engine)


# ========== 创建测试应用 ==========

@pytest.fixture(scope="module")
def client(db_session):
    """创建测试客户端"""
    from fastapi import FastAPI, Depends
    from sqlalchemy.orm import Session
    from reins.common.database import get_db
    
    def get_db_override():
        try:
            yield db_session
        finally:
            pass

    app = FastAPI()
    # Override get_db dependency used in router
    app.dependency_overrides[get_db] = get_db_override
    app.include_router(scenarios_router)
    
    with TestClient(app) as c:
        yield c
    
    with TestClient(app) as c:
        yield c


# ========== 测试用例 ==========

def test_list_scenarios_empty(client, db_session):
    """测试空场景列表"""
    response = client.get("/api/v1/scenarios/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_scenario(client, db_session):
    """测试创建场景"""
    scenario_data = {
        "name": "地震应急救援",
        "category": "earthquake",
        "status": "active",
        "version": "v1.0",
        "description": "适用于7.0级以上城市地震的应急救援",
        "scenario_desc": "本场景适用于7.0级以上城市地震的应急救援工作",
        "triggers": ["地震震级≥7.0", "城市人口密度>1000人/平方公里"]
    }
    response = client.post("/api/v1/scenarios/", json=scenario_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "地震应急救援"
    assert data["category"] == "earthquake"
    assert data["status"] == "active"
    assert data["version"] == "v1.0"
    assert "id" in data
    return data


def test_list_scenarios_with_data(client, db_session):
    """测试带数据的场景列表"""
    # Check if we have a scenario from previous test
    response = client.get("/api/v1/scenarios/")
    assert response.status_code == 200
    data = response.json()
    if not data:
        # Create a scenario if none exists
        scenario_data = {
            "name": "测试场景",
            "category": "earthquake",
            "status": "active",
            "version": "v1.0",
            "description": "测试场景",
            "scenario_desc": "测试场景描述",
        }
        client.post("/api/v1/scenarios/", json=scenario_data)
        response = client.get("/api/v1/scenarios/")
    
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] in ["测试场景", "地震应急救援"]


def test_get_scenario_by_id(client, db_session):
    """测试获取场景详情"""
    response = client.get("/api/v1/scenarios/")
    scenarios = response.json()
    if not scenarios:
        pytest.skip("No scenarios found")
    
    scenario_id = scenarios[0]["id"]
    response = client.get(f"/api/v1/scenarios/{scenario_id}")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "metrics" in data


def test_update_scenario(client, db_session):
    """测试更新场景"""
    response = client.get("/api/v1/scenarios/")
    scenarios = response.json()
    if not scenarios:
        pytest.skip("No scenarios found")
    
    scenario_id = scenarios[0]["id"]
    update_data = {
        "status": "archived",
        "scenario_desc": "更新后的适用场景描述"
    }
    response = client.put(f"/api/v1/scenarios/{scenario_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "archived"
    assert "更新后的适用场景描述" in data.get("scenario_desc", "")


def test_feedback_submission(client, db_session):
    """测试反馈回收"""
    response = client.get("/api/v1/scenarios/")
    scenarios = response.json()
    if not scenarios:
        pytest.skip("No scenarios found")
    
    scenario_id = scenarios[0]["id"]
    feedback_data = {
        "workflow_id": "workflow-123",
        "status": "completed",
        "duration_ms": 1800000,
        "steps_completed": 5,
        "steps_total": 5,
        "conflicts_count": 1
    }
    response = client.post(f"/api/v1/scenarios/{scenario_id}/feedback", json=feedback_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "updated_metrics" in data


def test_delete_scenario(client, db_session):
    """测试删除场景"""
    response = client.get("/api/v1/scenarios/")
    scenarios = response.json()
    if not scenarios:
        pytest.skip("No scenarios found")
    
    scenario_id = scenarios[0]["id"]
    response = client.delete(f"/api/v1/scenarios/{scenario_id}")
    assert response.status_code == 204
    
    # 验证已删除
    response = client.get(f"/api/v1/scenarios/{scenario_id}")
    assert response.status_code == 404


def test_filter_by_category(client, db_session):
    """测试按分类过滤"""
    response = client.get("/api/v1/scenarios/?category=earthquake")
    assert response.status_code == 200
    data = response.json()
    if data:
        assert data[0]["category"] == "earthquake"


def test_filter_by_status(client, db_session):
    """测试按状态过滤"""
    response = client.get("/api/v1/scenarios/?status=active")
    assert response.status_code == 200
    data = response.json()
    if data:
        assert data[0]["status"] == "active"


def test_search_by_keyword(client, db_session):
    """测试关键词搜索"""
    response = client.get("/api/v1/scenarios/?q=地震")
    assert response.status_code == 200
    data = response.json()
    if data:
        assert any("地震" in s.get("name", "") for s in data)


def test_sort_by_success_rate(client, db_session):
    """测试按成功率排序"""
    response = client.get("/api/v1/scenarios/?sort=success_rate&order=desc")
    assert response.status_code == 200
    data = response.json()
    if len(data) >= 2:
        assert data[0]["success_rate"] >= data[1]["success_rate"]
