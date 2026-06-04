"""
注入管理 API 单元测试

MAK-202: 后端-注入管理 API 单元测试

覆盖：规则列表、规则更新、状态查询
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from grasp.api.inject import router as inject_router
from models.grasp_inject import Base as InjectBase, GraspInjectRule, GraspInjectLog


# ========== 测试数据库 ==========

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_inject.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def db_session():
    """创建测试数据库session"""
    InjectBase.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        InjectBase.metadata.drop_all(bind=engine)


# ========== 创建测试应用 ==========

@pytest.fixture(scope="module")
def client(db_session):
    """创建测试客户端"""
    from fastapi import FastAPI
    from reins.common.database import get_db
    
    def get_db_override():
        try:
            yield db_session
        finally:
            pass

    app = FastAPI()
    app.dependency_overrides[get_db] = get_db_override
    app.include_router(inject_router)
    
    with TestClient(app) as c:
        yield c


# ========== 测试用例 ==========

def test_list_rules_empty(client, db_session):
    """测试空规则列表"""
    response = client.get("/api/v1/grasp/inject/rules")
    assert response.status_code == 200
    assert response.json() == []


def test_create_rule(client, db_session):
    """测试创建规则（通过直接插入）"""
    rule = GraspInjectRule(
        name="任务完成自动注入",
        trigger_condition="task.status=done",
        target_kb="default",
        enabled=True
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule


def test_list_rules(client, db_session):
    """测试获取规则列表"""
    response = client.get("/api/v1/grasp/inject/rules")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_update_rule(client, db_session):
    """测试更新规则（启用/禁用）"""
    # 创建规则
    rule = GraspInjectRule(
        name="测试规则",
        trigger_condition="task.status=done",
        target_kb="default",
        enabled=True
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    rule_id = rule.id
    
    # 禁用
    update_data = {"enabled": False}
    response = client.patch(f"/api/v1/grasp/inject/rules/{rule_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["rule"]["enabled"] is False
    
    # 再启用
    update_data = {"enabled": True}
    response = client.patch(f"/api/v1/grasp/inject/rules/{rule_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["rule"]["enabled"] is True


def test_disable_then_enable_rule(client, db_session):
    """测试规则多次切换状态"""
    # 创建规则
    rule = GraspInjectRule(
        name="多次切换测试规则",
        trigger_condition="workflow.status=completed",
        target_kb="experience",
        enabled=False
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    rule_id = rule.id
    
    # 启用
    response = client.patch(f"/api/v1/grasp/inject/rules/{rule_id}", json={"enabled": True})
    assert response.status_code == 200
    assert response.json()["rule"]["enabled"] is True
    
    # 再禁用
    response = client.patch(f"/api/v1/grasp/inject/rules/{rule_id}", json={"enabled": False})
    assert response.status_code == 200
    assert response.json()["rule"]["enabled"] is False


def test_get_status(client, db_session):
    """测试获取注入服务状态"""
    response = client.get("/api/v1/grasp/inject/status")
    assert response.status_code == 200
    data = response.json()
    assert "service_status" in data
    assert "recent_injections" in data
    assert isinstance(data["recent_injections"], list)


def test_update_nonexistent_rule(client):
    """测试更新不存在的规则"""
    update_data = {"enabled": False}
    response = client.patch("/api/v1/grasp/inject/rules/nonexistent-id", json=update_data)
    assert response.status_code == 404


def test_rule_persistence(client, db_session):
    """测试规则持久化"""
    # 创建规则
    rule = GraspInjectRule(
        name="持久化测试规则",
        trigger_condition="dispute.status=resolved",
        target_kb="教训库",
        enabled=False
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    rule_id = rule.id
    
    # 验证规则已持久化
    response = client.get("/api/v1/grasp/inject/rules/")
    assert response.status_code == 200
    rules = response.json()
    rule_ids = [r["id"] for r in rules]
    assert rule_id in rule_ids
    
    # 更新规则状态
    response = client.patch(f"/api/v1/grasp/inject/rules/{rule_id}", json={"enabled": True})
    assert response.status_code == 200
    
    # 重新查询验证更新已持久化
    response = client.get("/api/v1/grasp/inject/rules/")
    rules = response.json()
    rule_after = next((r for r in rules if r["id"] == rule_id), None)
    assert rule_after is not None
    assert rule_after["enabled"] is True
