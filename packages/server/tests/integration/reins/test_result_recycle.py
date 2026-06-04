"""
MAK-221: 结果回收单元测试

测试范围:
1. POST /api/v1/tasks/{task_id}/complete - 任务完成
   - 状态更新为 done
   - Goal 进度自动计算
2. POST /api/v1/tasks/{task_id}/fail - 任务失败
   - retry_count < 3 时重新派发（status = todo）
   - retry_count >= 3 时标记 blocked
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sys
from pathlib import Path

# 添加 src 到路径
src_dir = str(Path(__file__).parent.parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from api.server import create_app
from reins.common.database import get_db
from models.base import Base
from persistence.tables import metadata as core_metadata, agents, tasks, goals, projects, disputes, workflows, workflow_steps, task_activity_log, heartbeat_logs, task_failure_log
# Import ORM models to register them with Base.metadata
from models.scenario import Scenario, ScenarioStep
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


# 重写依赖项
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """每个测试前后的设置和清理"""
    # 创建表 - Core tables first, then ORM tables
    core_metadata.create_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    # 清理表
    Base.metadata.drop_all(bind=engine)
    core_metadata.drop_all(bind=engine)


def test_task_complete_status_update(client):
    """测试任务完成 - 状态更新为 done"""
    # 准备数据：创建一个任务
    db = TestingSessionLocal()
    
    # 先插入 agent
    import json
    from datetime import datetime
    capabilities_json = json.dumps(["capability1"])
    db.execute(text("""
        INSERT INTO agents (id, name, capabilities, status, address, metadata, 
                           load, current_tasks, trigger_mode, poll_interval_seconds, registered_at, last_heartbeat)
        VALUES (:id, :name, :capabilities, :status, :address, :metadata,
                :load, :current_tasks, :trigger_mode, :poll_interval_seconds, :registered_at, :last_heartbeat)
    """), {
        "id": 'agent-001',
        "name": 'Test Agent 1',
        "capabilities": capabilities_json,
        "status": 'online',
        "address": 'localhost:8080',
        "metadata": '{}',
        "load": 0,
        "current_tasks": 0,
        "trigger_mode": 'sse',
        "poll_interval_seconds": 10,
        "registered_at": datetime.now(),
        "last_heartbeat": datetime.now()
    })
    
    # 插入任务
    from datetime import datetime
    db.execute(text("""
        INSERT INTO tasks (id, title, description, goal_id, priority, assigned_agent, status, created_at, updated_at)
        VALUES ('task-complete-test', 'Complete Test Task', 'Task to test completion', '1', 2, 'agent-001', 'in_progress', :now, :now)
    """), {"now": datetime.now()})
    
    db.commit()
    
    # 发送完成请求
    complete_request = {
        "status": "done",
        "result": "Task completed successfully",
        "duration_ms": 1000
    }
    
    response = client.post("/api/v1/tasks/task-complete-test/complete", json=complete_request)
    
    # 断言
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["task_id"] == "task-complete-test"
    
    # 验证数据库中的状态更新
    result = db.execute(text("SELECT status FROM tasks WHERE id = 'task-complete-test'")).fetchone()
    assert result[0] == "done"


def test_task_complete_goal_progress(client):
    """测试任务完成 - Goal 进度自动计算"""
    # 准备数据：创建一个 goal 和多个任务
    db = TestingSessionLocal()
    
    # 先插入 agent
    import json
    from datetime import datetime
    capabilities_json = json.dumps(["capability1"])
    db.execute(text("""
        INSERT INTO agents (id, name, capabilities, status, address, metadata, 
                           load, current_tasks, trigger_mode, poll_interval_seconds, registered_at, last_heartbeat)
        VALUES (:id, :name, :capabilities, :status, :address, :metadata,
                :load, :current_tasks, :trigger_mode, :poll_interval_seconds, :registered_at, :last_heartbeat)
    """), {
        "id": 'agent-001',
        "name": 'Test Agent 1',
        "capabilities": capabilities_json,
        "status": 'online',
        "address": 'localhost:8080',
        "metadata": '{}',
        "load": 0,
        "current_tasks": 0,
        "trigger_mode": 'sse',
        "poll_interval_seconds": 10,
        "registered_at": datetime.now(),
        "last_heartbeat": datetime.now()
    })
    
    # 插入 goal
    from datetime import datetime
    db.execute(text("""
        INSERT INTO goals (id, title, description, status, progress, created_at, updated_at)
        VALUES ('1', 'Test Goal', 'Goal for testing progress', 'in_progress', 0.0, :now, :now)
    """), {"now": datetime.now()})
    
    # 插入多个任务，其中一些已完成，一些待完成
    db.execute(text("""
        INSERT INTO tasks (id, title, description, goal_id, priority, assigned_agent, status, created_at, updated_at)
        VALUES 
        ('task-goal-1', 'Goal Task 1', 'First task for goal', '1', 2, 'agent-001', 'done', :now, :now),
        ('task-goal-2', 'Goal Task 2', 'Second task for goal', '1', 2, 'agent-001', 'todo', :now, :now),
        ('task-goal-3', 'Goal Task 3', 'Third task for goal', '1', 2, 'agent-001', 'todo', :now, :now)
    """), {"now": datetime.now()})
    
    db.commit()
    
    # 在测试前确认初始进度
    initial_goal = db.execute(text("SELECT progress FROM goals WHERE id = 1")).fetchone()
    assert initial_goal[0] == 0.0  # 初始进度为0
    
    # 完成第二个任务
    complete_request = {
        "status": "done",
        "result": "Second task completed",
        "duration_ms": 1500
    }
    
    response = client.post("/api/v1/tasks/task-goal-2/complete", json=complete_request)
    
    # 断言
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["task_id"] == "task-goal-2"
    assert data["goal_progress"] is not None
    assert data["goal_progress"]["completed_tasks"] == 2  # 现在有2个完成的任务
    assert data["goal_progress"]["total_tasks"] == 3
    assert data["goal_progress"]["progress_percent"] == 66.67  # 2/3 = 66.67%
    
    # 验证数据库中的进度更新
    updated_goal = db.execute(text("SELECT progress FROM goals WHERE id = 1")).fetchone()
    assert abs(updated_goal[0] - 66.67) < 0.01


def test_task_fail_retry_less_than_3(client):
    """测试任务失败 - retry_count < 3 时重新派发（status = todo）"""
    # 准备数据：创建一个任务
    db = TestingSessionLocal()
    
    # 先插入 agent
    import json
    from datetime import datetime
    capabilities_json = json.dumps(["capability1"])
    db.execute(text("""
        INSERT INTO agents (id, name, capabilities, status, address, metadata, 
                           load, current_tasks, trigger_mode, poll_interval_seconds, registered_at, last_heartbeat)
        VALUES (:id, :name, :capabilities, :status, :address, :metadata,
                :load, :current_tasks, :trigger_mode, :poll_interval_seconds, :registered_at, :last_heartbeat)
    """), {
        "id": 'agent-001',
        "name": 'Test Agent 1',
        "capabilities": capabilities_json,
        "status": 'online',
        "address": 'localhost:8080',
        "metadata": '{}',
        "load": 0,
        "current_tasks": 0,
        "trigger_mode": 'sse',
        "poll_interval_seconds": 10,
        "registered_at": datetime.now(),
        "last_heartbeat": datetime.now()
    })
    
    # 插入任务
    from datetime import datetime
    db.execute(text("""
        INSERT INTO tasks (id, title, description, goal_id, priority, assigned_agent, status, retry_count, created_at, updated_at)
        VALUES ('task-fail-test-1', 'Fail Test Task 1', 'Task to test failure with retry < 3', '1', 2, 'agent-001', 'in_progress', 1, :now, :now)
    """), {"now": datetime.now()})
    
    db.commit()
    
    # 发送失败请求，retry_count < max_retries
    fail_request = {
        "error_type": "execution_error",
        "error_message": "Something went wrong but can be retried",
        "retry_count": 1,  # 小于默认最大重试次数3
        "max_retries": 3
    }
    
    response = client.post("/api/v1/tasks/task-fail-test-1/fail", json=fail_request)
    
    # 断言
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["task_id"] == "task-fail-test-1"
    assert data["next_action"] == "retry"
    assert data["retry_count"] == 1
    assert data["max_retries"] == 3
    
    # 验证数据库中的状态更新为 todo（重新派发）
    result = db.execute(text("SELECT status FROM tasks WHERE id = 'task-fail-test-1'")).fetchone()
    assert result[0] == "todo"
    
    # 验证重试计数更新
    retry_count_result = db.execute(text("SELECT retry_count FROM tasks WHERE id = 'task-fail-test-1'")).fetchone()
    assert retry_count_result[0] == 2  # 应该增加到2


def test_task_fail_retry_greater_equal_3(client):
    """测试任务失败 - retry_count >= 3 时标记 blocked"""
    # 准备数据：创建一个任务
    db = TestingSessionLocal()
    
    # 先插入 agent
    import json
    from datetime import datetime
    capabilities_json = json.dumps(["capability1"])
    db.execute(text("""
        INSERT INTO agents (id, name, capabilities, status, address, metadata, 
                           load, current_tasks, trigger_mode, poll_interval_seconds, registered_at, last_heartbeat)
        VALUES (:id, :name, :capabilities, :status, :address, :metadata,
                :load, :current_tasks, :trigger_mode, :poll_interval_seconds, :registered_at, :last_heartbeat)
    """), {
        "id": 'agent-001',
        "name": 'Test Agent 1',
        "capabilities": capabilities_json,
        "status": 'online',
        "address": 'localhost:8080',
        "metadata": '{}',
        "load": 0,
        "current_tasks": 0,
        "trigger_mode": 'sse',
        "poll_interval_seconds": 10,
        "registered_at": datetime.now(),
        "last_heartbeat": datetime.now()
    })
    
    # 插入任务
    from datetime import datetime
    db.execute(text("""
        INSERT INTO tasks (id, title, description, goal_id, priority, assigned_agent, status, retry_count, created_at, updated_at)
        VALUES ('task-fail-test-2', 'Fail Test Task 2', 'Task to test failure with retry >= 3', '1', 2, 'agent-001', 'in_progress', 3, :now, :now)
    """), {"now": datetime.now()})
    
    db.commit()
    
    # 发送失败请求，retry_count >= max_retries
    fail_request = {
        "error_type": "execution_error",
        "error_message": "Something went wrong and max retries exceeded",
        "retry_count": 3,  # 等于最大重试次数
        "max_retries": 3
    }
    
    response = client.post("/api/v1/tasks/task-fail-test-2/fail", json=fail_request)
    
    # 断言
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["task_id"] == "task-fail-test-2"
    assert data["next_action"] == "blocked"
    assert data["retry_count"] == 3
    assert data["max_retries"] == 3
    
    # 验证数据库中的状态更新为 blocked
    result = db.execute(text("SELECT status FROM tasks WHERE id = 'task-fail-test-2'")).fetchone()
    assert result[0] == "blocked"
    
    # 验证 blocked_reason 设置
    reason_result = db.execute(text("SELECT blocked_reason FROM tasks WHERE id = 'task-fail-test-2'")).fetchone()
    assert "Blocked after 3 retries" in reason_result[0] if reason_result[0] else False


def test_task_fail_max_retries_exceeded(client):
    """测试任务失败 - retry_count 超过 max_retries 时标记 blocked"""
    # 准备数据：创建一个任务
    db = TestingSessionLocal()
    
    # 先插入 agent
    import json
    from datetime import datetime
    capabilities_json = json.dumps(["capability1"])
    db.execute(text("""
        INSERT INTO agents (id, name, capabilities, status, address, metadata, 
                           load, current_tasks, trigger_mode, poll_interval_seconds, registered_at, last_heartbeat)
        VALUES (:id, :name, :capabilities, :status, :address, :metadata,
                :load, :current_tasks, :trigger_mode, :poll_interval_seconds, :registered_at, :last_heartbeat)
    """), {
        "id": 'agent-001',
        "name": 'Test Agent 1',
        "capabilities": capabilities_json,
        "status": 'online',
        "address": 'localhost:8080',
        "metadata": '{}',
        "load": 0,
        "current_tasks": 0,
        "trigger_mode": 'sse',
        "poll_interval_seconds": 10,
        "registered_at": datetime.now(),
        "last_heartbeat": datetime.now()
    })
    
    # 插入任务
    from datetime import datetime
    db.execute(text("""
        INSERT INTO tasks (id, title, description, goal_id, priority, assigned_agent, status, retry_count, created_at, updated_at)
        VALUES ('task-fail-test-3', 'Fail Test Task 3', 'Task to test failure with retry > max_retries', '1', 2, 'agent-001', 'in_progress', 4, :now, :now)
    """), {"now": datetime.now()})
    
    db.commit()
    
    # 发送失败请求，retry_count > max_retries
    fail_request = {
        "error_type": "execution_error",
        "error_message": "Something went wrong and way past max retries",
        "retry_count": 4,  # 超过最大重试次数
        "max_retries": 3
    }
    
    response = client.post("/api/v1/tasks/task-fail-test-3/fail", json=fail_request)
    
    # 断言
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["task_id"] == "task-fail-test-3"
    assert data["next_action"] == "blocked"
    assert data["retry_count"] == 4
    assert data["max_retries"] == 3
    
    # 验证数据库中的状态更新为 blocked
    result = db.execute(text("SELECT status FROM tasks WHERE id = 'task-fail-test-3'")).fetchone()
    assert result[0] == "blocked"
