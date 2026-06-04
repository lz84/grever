"""
注入管理 API 业务测试

MAK-212: 后端-注入管理 API 业务测试

覆盖：创建规则 → 启用/禁用 → 查询状态 → 验证持久化
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from grasp.api.inject import router as inject_router
from models.grasp_inject import Base as InjectBase, GraspInjectRule, GraspInjectLog


# ========== 测试数据库 ==========

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_inject_business.db"
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

def test_business_flow_full(client, db_session):
    """
    完整业务流程测试：
    1. 创建规则
    2. 启用规则
    3. 查询状态
    4. 验证持久化
    """
    
    # ========== 步骤1: 创建规则 ==========
    print("步骤1: 创建规则")
    db_session.query(GraspInjectRule).delete()
    db_session.commit()
    
    rule = GraspInjectRule(
        name="业务流程测试规则",
        trigger_condition="task.status=done",
        target_kb="default",
        enabled=False
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    rule_id = rule.id
    
    print(f"创建规则成功: {rule_id}")
    
    # ========== 步骤2: 启用规则 ==========
    print("步骤2: 启用规则")
    response = client.patch(f"/api/v1/grasp/inject/rules/{rule_id}", json={"enabled": True})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["rule"]["enabled"] is True
    assert data["rule"]["id"] == rule_id
    print("启用规则成功")
    
    # ========== 步骤3: 查询状态 ==========
    print("步骤3: 查询状态")
    
    # 查询所有规则
    response = client.get("/api/v1/grasp/inject/rules")
    assert response.status_code == 200
    rules = response.json()
    assert len(rules) >= 1
    enabled_rule = next((r for r in rules if r["id"] == rule_id), None)
    assert enabled_rule is not None
    assert enabled_rule["enabled"] is True
    print(f"查询所有规则成功: 共{len(rules)}条，启用状态正确")
    
    # 查询注入状态
    response = client.get("/api/v1/grasp/inject/status")
    assert response.status_code == 200
    status_data = response.json()
    assert "service_status" in status_data
    assert "recent_injections" in status_data
    print(f"查询注入状态成功: service_status={status_data['service_status']}")
    
    # ========== 步骤4: 验证持久化 ==========
    print("步骤4: 验证持久化")
    
    # 重新查询规则
    response = client.get("/api/v1/grasp/inject/rules")
    rules_after = response.json()
    rule_after = next((r for r in rules_after if r["id"] == rule_id), None)
    assert rule_after is not None
    assert rule_after["enabled"] is True
    print("持久化验证 - 规则状态正确")
    
    # 2. 更新规则并再次验证
    response = client.patch(f"/api/v1/grasp/inject/rules/{rule_id}", json={"enabled": False})
    assert response.status_code == 200
    
    # 重新查询验证更新已持久化
    response = client.get("/api/v1/grasp/inject/rules")
    rules_final = response.json()
    rule_final = next((r for r in rules_final if r["id"] == rule_id), None)
    assert rule_final is not None
    assert rule_final["enabled"] is False
    print("持久化验证 - 更新已保存")
    
    # ========== 步骤5: 禁用规则 ==========
    print("步骤5: 禁用规则")
    response = client.patch(f"/api/v1/grasp/inject/rules/{rule_id}", json={"enabled": False})
    assert response.status_code == 200
    data = response.json()
    assert data["rule"]["enabled"] is False
    print("禁用规则成功")
    
    # ========== 步骤6: 再次查询验证 ========== 
    print("步骤6: 再次查询验证")
    response = client.get("/api/v1/grasp/inject/rules")
    rules = response.json()
    disabled_rule = next((r for r in rules if r["id"] == rule_id), None)
    assert disabled_rule is not None
    assert disabled_rule["enabled"] is False
    print("最终验证 - 禁用状态正确")
    
    # ========== 步骤7: 添加注入日志并查询 ==========
    print("步骤7: 添加注入日志并查询")
    
    log = GraspInjectLog(
        source="task",
        type="task_result",
        cognition_count=3,
        status="success",
        extra={"test": "business_flow"}
    )
    db_session.add(log)
    db_session.commit()
    log_id = log.id
    
    response = client.get("/api/v1/grasp/inject/status")
    assert response.status_code == 200
    status_data = response.json()
    assert len(status_data["recent_injections"]) >= 1
    print("注入日志查询成功")


def test_multiple_rules(client, db_session):
    """测试多个规则的完整生命周期"""
    
    # 清空
    db_session.query(GraspInjectRule).delete()
    db_session.commit()
    
    # 创建多个规则
    rules_data = [
        {"name": "规则1", "trigger_condition": "task.status=done", "target_kb": "default"},
        {"name": "规则2", "trigger_condition": "workflow.status=completed", "target_kb": "experience"},
        {"name": "规则3", "trigger_condition": "dispute.status=resolved", "target_kb": "教训库"},
    ]
    
    rule_ids = []
    for data in rules_data:
        rule = GraspInjectRule(**data, enabled=True)
        db_session.add(rule)
        db_session.commit()
        db_session.refresh(rule)
        rule_ids.append(rule.id)
    
    # 查询所有规则
    response = client.get("/api/v1/grasp/inject/rules")
    assert response.status_code == 200
    rules = response.json()
    assert len(rules) == 3
    
    # 禁用其中2个
    for i, rule_id in enumerate(rule_ids[:2]):
        response = client.patch(f"/api/v1/grasp/inject/rules/{rule_id}", json={"enabled": False})
        assert response.status_code == 200
        assert response.json()["rule"]["enabled"] is False
    
    # 验证状态
    response = client.get("/api/v1/grasp/inject/rules")
    rules = response.json()
    
    disabled_count = sum(1 for r in rules if not r["enabled"])
    enabled_count = sum(1 for r in rules if r["enabled"])
    
    assert disabled_count == 2
    assert enabled_count == 1
    
    print(f"批量测试完成: 共{len(rules)}条规则，{enabled_count}个启用，{disabled_count}个禁用")


def test_status_contains_recent_injections(client, db_session):
    """测试状态API包含最近注入记录"""
    
    # 清空
    db_session.query(GraspInjectLog).delete()
    db_session.commit()
    
    # 创建多条日志
    log_data = [
        {"source": "task", "type": "task_result", "cognition_count": 2, "status": "success"},
        {"source": "workflow", "type": "workflow_result", "cognition_count": 5, "status": "success"},
        {"source": "dispute", "type": "dispute_result", "cognition_count": 1, "status": "failed"},
    ]
    
    for data in log_data:
        log = GraspInjectLog(**data)
        db_session.add(log)
        db_session.commit()
    
    # 查询状态
    response = client.get("/api/v1/grasp/inject/status")
    assert response.status_code == 200
    status_data = response.json()
    
    # 验证最近注入记录
    recent_injections = status_data["recent_injections"]
    assert len(recent_injections) >= 3
    
    # 验证日志结构
    for log in recent_injections:
        assert "id" in log
        assert "source" in log
        assert "type" in log
        assert "cognition_count" in log
        assert "status" in log
        assert "created_at" in log
    
    print(f"最近注入记录验证通过: {len(recent_injections)}条记录")
