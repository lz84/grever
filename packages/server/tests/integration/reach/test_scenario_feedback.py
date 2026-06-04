"""
MAK-222: 场景反馈单元测试

测试范围:
1. POST /api/v1/scenarios/{scenario_id}/feedback - 场景反馈
   - 更新成功率/执行次数/平均耗时
   - 版本号自动提升
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sys
from pathlib import Path
from datetime import datetime

# 添加 src 到路径
src_dir = str(Path(__file__).parent.parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from api.server import create_app
from reins.common.database import get_db
from models.base import Base
from persistence.tables import metadata as core_metadata
# Import ORM models to register them with Base.metadata
from models.scenario import Scenario
from models.goal import Goal
from models.task import Task
from models.workflow import Workflow, WorkflowStep


# 创建内存数据库引擎
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def app():
    """创建测试应用实例"""
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    """创建测试客户端"""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """每个测试前后的设置和清理"""
    # 创建表 - Core tables first, then ORM tables
    core_metadata.create_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # 重写依赖项
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    application = create_app()
    application.dependency_overrides[get_db] = override_get_db
    
    yield
    
    # 清理表
    Base.metadata.drop_all(bind=engine)
    core_metadata.drop_all(bind=engine)


def test_scenario_feedback_updates_success_rate(client):
    """测试场景反馈 - 更新成功率"""
    # 准备数据：创建一个场景
    db = TestingSessionLocal()
    
    # 插入场景
    db.execute(text("""
        INSERT INTO scenarios (id, name, category, status, version, description, scenario_desc,
                              total_executions, success_count, failed_count, avg_duration_ms, success_rate, usage_count, created_at, updated_at)
        VALUES ('scenario-001', 'Test Scenario', 'general', 'active', 'v1.0', 'A test scenario', 'Detailed description',
                2, 1, 1, 1000.0, 50.0, 2, :now, :now)
    """), {"now": datetime.now()})
    
    db.commit()
    
    # 发送反馈请求 - 成功执行
    feedback_request = {
        "workflow_id": "test-workflow-001",
        "status": "completed",
        "duration_ms": 1200,
        "steps_completed": 3,
        "steps_total": 5,
        "conflicts_count": 0,
        "user_modifications": None
    }
    
    response = client.post("/api/v1/scenarios/scenario-001/feedback", json=feedback_request)
    
    # 断言
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Feedback recorded successfully"
    
    # 验证数据库中的成功率更新
    result = db.execute(text("SELECT success_count, total_executions, success_rate FROM scenarios WHERE id = 'scenario-001'")).fetchone()
    assert result[0] == 2  # 成功次数应增加到2
    assert result[1] == 3  # 总执行次数应增加到3
    assert abs(result[2] - 66.67) < 0.01  # 新的成功率应该是 2/3 = 66.67%
    
    db.close()


def test_scenario_feedback_updates_execution_counts(client):
    """测试场景反馈 - 更新执行次数"""
    # 准备数据：创建一个场景
    db = TestingSessionLocal()
    
    # 插入场景
    db.execute(text("""
        INSERT INTO scenarios (id, name, category, status, version, description, scenario_desc,
                              total_executions, success_count, failed_count, avg_duration_ms, success_rate, usage_count, created_at, updated_at)
        VALUES ('scenario-002', 'Test Scenario 2', 'general', 'active', 'v1.0', 'Another test scenario', 'Detailed description',
                1, 1, 0, 800.0, 100.0, 1, :now, :now)
    """), {"now": datetime.now()})
    
    db.commit()
    
    # 发送反馈请求 - 失败执行
    feedback_request = {
        "workflow_id": "test-workflow-002",
        "status": "failed",
        "duration_ms": 900,
        "steps_completed": 2,
        "steps_total": 5,
        "conflicts_count": 1,
        "user_modifications": None
    }
    
    response = client.post("/api/v1/scenarios/scenario-002/feedback", json=feedback_request)
    
    # 断言
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # 验证数据库中的执行次数更新
    result = db.execute(text("SELECT total_executions, success_count, failed_count FROM scenarios WHERE id = 'scenario-002'")).fetchone()
    assert result[0] == 2  # 总执行次数应增加到2
    assert result[1] == 1  # 成功次数保持1
    assert result[2] == 1  # 失败次数应增加到1
    
    db.close()


def test_scenario_feedback_updates_avg_duration(client):
    """测试场景反馈 - 更新平均耗时"""
    # 准备数据：创建一个场景，初始平均耗时为1000ms，总执行2次
    db = TestingSessionLocal()
    
    # 插入场景
    db.execute(text("""
        INSERT INTO scenarios (id, name, category, status, version, description, scenario_desc,
                              total_executions, success_count, failed_count, avg_duration_ms, success_rate, usage_count, created_at, updated_at)
        VALUES ('scenario-003', 'Test Scenario 3', 'general', 'active', 'v1.0', 'Third test scenario', 'Detailed description',
                2, 2, 0, 1000.0, 100.0, 2, :now, :now)
    """), {"now": datetime.now()})
    
    db.commit()
    
    # 发送反馈请求 - 新的执行耗时为1400ms
    feedback_request = {
        "workflow_id": "test-workflow-003",
        "status": "completed",
        "duration_ms": 1400,
        "steps_completed": 5,
        "steps_total": 5,
        "conflicts_count": 0,
        "user_modifications": None
    }
    
    response = client.post("/api/v1/scenarios/scenario-003/feedback", json=feedback_request)
    
    # 断言
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # 验证数据库中的平均耗时更新
    # 原来是 (1000*2)ms 总耗时，现在加上1400ms变成 (2000+1400)/3 = 1133.33ms
    result = db.execute(text("SELECT avg_duration_ms, total_executions FROM scenarios WHERE id = 'scenario-003'")).fetchone()
    assert result[1] == 3  # 总执行次数应为3
    assert abs(result[0] - 1133.33) < 0.01  # 新的平均耗时
    
    db.close()


def test_scenario_feedback_updates_version(client):
    """测试场景反馈 - 版本号自动提升"""
    # 准备数据：创建一个场景
    db = TestingSessionLocal()
    
    # 插入场景
    db.execute(text("""
        INSERT INTO scenarios (id, name, category, status, version, description, scenario_desc,
                              total_executions, success_count, failed_count, avg_duration_ms, success_rate, usage_count, created_at, updated_at)
        VALUES ('scenario-004', 'Test Scenario 4', 'general', 'active', 'v1.0', 'Fourth test scenario', 'Detailed description',
                0, 0, 0, NULL, 0.0, 0, :now, :now)
    """), {"now": datetime.now()})
    
    db.commit()
    
    # 发送反馈请求
    feedback_request = {
        "workflow_id": "test-workflow-004",
        "status": "completed",
        "duration_ms": 1100,
        "steps_completed": 5,
        "steps_total": 5,
        "conflicts_count": 0,
        "user_modifications": None
    }
    
    response = client.post("/api/v1/scenarios/scenario-004/feedback", json=feedback_request)
    
    # 断言
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # 验证数据库中的版本号提升
    result = db.execute(text("SELECT version FROM scenarios WHERE id = 'scenario-004'")).fetchone()
    assert result[0] == "v1.1"  # 版本号应从 v1.0 提升到 v1.1
    
    db.close()


def test_scenario_feedback_version_increment(client):
    """测试场景反馈 - 版本号递增"""
    # 准备数据：创建一个场景，版本已经是v1.1
    db = TestingSessionLocal()
    
    # 插入场景
    db.execute(text("""
        INSERT INTO scenarios (id, name, category, status, version, description, scenario_desc,
                              total_executions, success_count, failed_count, avg_duration_ms, success_rate, usage_count, created_at, updated_at)
        VALUES ('scenario-005', 'Test Scenario 5', 'general', 'active', 'v1.1', 'Fifth test scenario', 'Detailed description',
                1, 1, 0, 900.0, 100.0, 1, :now, :now)
    """), {"now": datetime.now()})
    
    db.commit()
    
    # 发送反馈请求
    feedback_request = {
        "workflow_id": "test-workflow-005",
        "status": "completed",
        "duration_ms": 1000,
        "steps_completed": 5,
        "steps_total": 5,
        "conflicts_count": 0,
        "user_modifications": None
    }
    
    response = client.post("/api/v1/scenarios/scenario-005/feedback", json=feedback_request)
    
    # 断言
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # 验证数据库中的版本号继续递增
    result = db.execute(text("SELECT version FROM scenarios WHERE id = 'scenario-005'")).fetchone()
    assert result[0] == "v1.2"  # 版本号应从 v1.1 提升到 v1.2
    
    db.close()


def test_scenario_feedback_scenario_not_found(client):
    """测试场景反馈 - 场景不存在时返回404"""
    # 发送反馈请求到不存在的场景
    feedback_request = {
        "workflow_id": "test-workflow-nonexistent",
        "status": "completed",
        "duration_ms": 1000,
        "steps_completed": 5,
        "steps_total": 5,
        "conflicts_count": 0,
        "user_modifications": None
    }
    
    response = client.post("/api/v1/scenarios/nonexistent-scenario/feedback", json=feedback_request)
    
    # 断言
    assert response.status_code == 404
    assert "Scenario not found" in response.text


def test_scenario_feedback_usage_count(client):
    """测试场景反馈 - 更新使用次数"""
    # 准备数据：创建一个场景
    db = TestingSessionLocal()
    
    # 插入场景
    db.execute(text("""
        INSERT INTO scenarios (id, name, category, status, version, description, scenario_desc,
                              total_executions, success_count, failed_count, avg_duration_ms, success_rate, usage_count, created_at, updated_at)
        VALUES ('scenario-006', 'Test Scenario 6', 'general', 'active', 'v1.0', 'Sixth test scenario', 'Detailed description',
                1, 1, 0, 800.0, 100.0, 1, :now, :now)
    """), {"now": datetime.now()})
    
    db.commit()
    
    # 发送反馈请求
    feedback_request = {
        "workflow_id": "test-workflow-006",
        "status": "completed",
        "duration_ms": 950,
        "steps_completed": 5,
        "steps_total": 5,
        "conflicts_count": 0,
        "user_modifications": None
    }
    
    response = client.post("/api/v1/scenarios/scenario-006/feedback", json=feedback_request)
    
    # 断言
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # 验证数据库中的使用次数更新
    result = db.execute(text("SELECT usage_count FROM scenarios WHERE id = 'scenario-006'")).fetchone()
    assert result[0] == 2  # 使用次数应从1增加到2
    
    db.close()