"""
L4-API-R-002 Reins Agent Task Operations API 测试

对照文档：docs/09-系统设计/25-测试用例总览.md → TC-API-R-002

覆盖用例：
- TC-API-R-002: Agent 任务操作
  - POST /api/v1/agents/{agent_id}/tasks/{task_id}/claim — Agent 认领任务
  - POST /api/v1/agents/{agent_id}/tasks/{task_id}/report — Agent 上报结果
"""

import json
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

src_dir = str(Path(__file__).parent.parent.parent.parent / 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from api.app_state import set_db_manager
from persistence.base import DatabaseConfig
from persistence.database import DatabaseManager


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        # agents 表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'offline',
                capabilities TEXT,
                capability_tags TEXT,
                current_tasks INTEGER DEFAULT 0,
                max_concurrent_tasks INTEGER DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # tasks 表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                goal_id TEXT,
                title TEXT,
                status TEXT DEFAULT 'todo',
                assigned_agent TEXT,
                result TEXT,
                project_id TEXT,
                estimated_hours REAL,
                actual_hours REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # task_activity_log 表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS task_activity_log (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT,
                reason TEXT,
                actor TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                extra TEXT
            )
        """))
        # execution_logs 表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS execution_logs (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                agent_id TEXT,
                action TEXT,
                input TEXT,
                output TEXT,
                status TEXT,
                duration_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT,
                result_summary TEXT,
                metadata TEXT
            )
        """))
        conn.commit()
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture
def client(test_db):
    """Create TestClient with in-memory SQLite and agent task operations router"""
    db_config = DatabaseConfig(provider="sqlite", path=":memory:")
    db_manager = DatabaseManager(db_config)
    db_manager._engine = test_db.get_bind()
    set_db_manager(db_manager)

    from reins.api.agent_task_operations import router as task_ops_router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(task_ops_router)
    with TestClient(app) as tc:
        yield tc


# ===========================================================================
# TC-API-R-002-01: POST /api/v1/agents/{agent_id}/tasks/{task_id}/claim — 认领任务
# ===========================================================================

class TestClaimTask:
    """TC-API-R-002-01: Agent 认领任务"""

    def test_claim_task_agent_not_found(self, client):
        """Agent 不存在返回 404"""
        response = client.post(
            "/api/v1/agents/nonexistent-agent/tasks/task-001/claim",
            json={}
        )
        assert response.status_code == 404
        assert "Agent not found" in response.json()["detail"]

    def test_claim_task_agent_not_available(self, client, test_db):
        """Agent 不在线返回 400"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "agent-offline", "name": "Offline Agent", "status": "offline", "created": now})
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-offline/tasks/task-001/claim",
            json={}
        )
        assert response.status_code == 400
        assert "not available" in response.json()["detail"]

    def test_claim_task_at_max_capacity(self, client, test_db):
        """Agent 达到最大任务数返回 429"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, current_tasks, max_concurrent_tasks, created_at)
            VALUES (:id, :name, :status, :current, :max, :created)
        """), {
            "id": "agent-full",
            "name": "Full Agent",
            "status": "online",
            "current": 5,
            "max": 5,
            "created": now,
        })
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-full/tasks/task-001/claim",
            json={}
        )
        assert response.status_code == 429
        assert "max capacity" in response.json()["detail"]

    def test_claim_task_not_found(self, client, test_db):
        """任务不存在返回 404"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "agent-001", "name": "Test Agent", "status": "online", "created": now})
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-001/tasks/nonexistent-task/claim",
            json={}
        )
        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]

    def test_claim_task_invalid_status(self, client, test_db):
        """任务状态不允许认领返回 400"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "agent-002", "name": "Test Agent", "status": "online", "created": now})
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, created_at)
            VALUES (:id, :title, :status, :created)
        """), {"id": "task-in-progress", "title": "In Progress Task", "status": "in_progress", "created": now})
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-002/tasks/task-in-progress/claim",
            json={}
        )
        assert response.status_code == 400
        assert "cannot be claimed" in response.json()["detail"]

    def test_claim_task_already_assigned(self, client, test_db):
        """任务已分配给其他 Agent 返回 409"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "agent-a", "name": "Agent A", "status": "online", "created": now})
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "agent-b", "name": "Agent B", "status": "online", "created": now})
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, assigned_agent, created_at)
            VALUES (:id, :title, :status, :agent, :created)
        """), {"id": "task-claimed", "title": "Claimed Task", "status": "todo", "agent": "agent-a", "created": now})
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-b/tasks/task-claimed/claim",
            json={}
        )
        assert response.status_code == 409
        assert "already assigned" in response.json()["detail"]

    def test_claim_task_success(self, client, test_db):
        """成功认领任务"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, current_tasks, max_concurrent_tasks, created_at)
            VALUES (:id, :name, :status, :current, :max, :created)
        """), {
            "id": "agent-claim-test",
            "name": "Claim Test Agent",
            "status": "online",
            "current": 1,
            "max": 5,
            "created": now,
        })
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, created_at)
            VALUES (:id, :title, :status, :created)
        """), {"id": "task-claim-test", "title": "Claim Test Task", "status": "todo", "created": now})
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-claim-test/tasks/task-claim-test/claim",
            json={"reason": "I can handle this", "estimated_hours": 4.5}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-claim-test"
        assert data["agent_id"] == "agent-claim-test"
        assert data["status"] == "in_progress"
        assert "claimed_at" in data

    def test_claim_task_without_reason(self, client, test_db):
        """不带 reason 认领任务"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "agent-no-reason", "name": "No Reason Agent", "status": "idle", "created": now})
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, created_at)
            VALUES (:id, :title, :status, :created)
        """), {"id": "task-no-reason", "title": "No Reason Task", "status": "pending", "created": now})
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-no-reason/tasks/task-no-reason/claim"
        )
        assert response.status_code == 200

    def test_claim_task_updates_agent_current_tasks(self, client, test_db):
        """认领后更新 Agent 当前任务数"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, current_tasks, max_concurrent_tasks, created_at)
            VALUES (:id, :name, :status, :current, :max, :created)
        """), {
            "id": "agent-update-count",
            "name": "Update Count Agent",
            "status": "online",
            "current": 2,
            "max": 5,
            "created": now,
        })
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, created_at)
            VALUES (:id, :title, :status, :created)
        """), {"id": "task-update-count", "title": "Update Count Task", "status": "unassigned", "created": now})
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-update-count/tasks/task-update-count/claim"
        )
        assert response.status_code == 200

        # 验证 current_tasks 已更新
        row = test_db.execute(
            text("SELECT current_tasks FROM agents WHERE id = :id"),
            {"id": "agent-update-count"}
        ).fetchone()
        assert row[0] == 3

    def test_claim_task_creates_activity_log(self, client, test_db):
        """认领任务创建活动日志"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "agent-log", "name": "Log Agent", "status": "online", "created": now})
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, created_at)
            VALUES (:id, :title, :status, :created)
        """), {"id": "task-log", "title": "Log Task", "status": "todo", "created": now})
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-log/tasks/task-log/claim",
            json={"reason": "Log test"}
        )
        assert response.status_code == 200

        # 验证活动日志存在
        log = test_db.execute(
            text("SELECT task_id, new_status, reason, actor FROM task_activity_log WHERE task_id = :id"),
            {"id": "task-log"}
        ).fetchone()
        assert log is not None
        assert log[0] == "task-log"
        assert log[1] == "claimed"
        assert log[2] == "Log Agent claimed task: Log test"
        assert log[3] == "agent-log"


# ===========================================================================
# TC-API-R-002-02: POST /api/v1/agents/{agent_id}/tasks/{task_id}/report — 上报结果
# ===========================================================================

class TestReportTask:
    """TC-API-R-002-02: Agent 上报任务结果"""

    def test_report_task_agent_not_found(self, client):
        """Agent 不存在返回 404"""
        response = client.post(
            "/api/v1/agents/nonexistent-agent/tasks/task-001/report",
            json={"status": "completed"}
        )
        assert response.status_code == 404
        assert "Agent not found" in response.json()["detail"]

    def test_report_task_not_found(self, client, test_db):
        """任务不存在返回 404"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "agent-report-001", "name": "Report Agent", "status": "online", "created": now})
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-report-001/tasks/nonexistent-task/report",
            json={"status": "completed"}
        )
        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]

    def test_report_task_not_assigned_to_agent(self, client, test_db):
        """任务未分配给该 Agent 返回 403"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "agent-report-a", "name": "Agent A", "status": "online", "created": now})
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "agent-report-b", "name": "Agent B", "status": "online", "created": now})
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, assigned_agent, created_at)
            VALUES (:id, :title, :status, :agent, :created)
        """), {"id": "task-report-001", "title": "Task A", "status": "in_progress", "agent": "agent-report-a", "created": now})
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-report-b/tasks/task-report-001/report",
            json={"status": "completed"}
        )
        assert response.status_code == 403
        assert "not assigned" in response.json()["detail"]

    def test_report_task_invalid_status(self, client, test_db):
        """无效上报状态返回 400"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "agent-invalid-status", "name": "Invalid Status Agent", "status": "online", "created": now})
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, assigned_agent, created_at)
            VALUES (:id, :title, :status, :agent, :created)
        """), {"id": "task-invalid-status", "title": "Invalid Status Task", "status": "in_progress", "agent": "agent-invalid-status", "created": now})
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-invalid-status/tasks/task-invalid-status/report",
            json={"status": "unknown_status"}
        )
        assert response.status_code == 400
        assert "Invalid report status" in response.json()["detail"]

    def test_report_task_completed_success(self, client, test_db):
        """成功上报完成任务"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, current_tasks, created_at)
            VALUES (:id, :name, :status, :current, :created)
        """), {"id": "agent-completed", "name": "Completed Agent", "status": "online", "current": 1, "created": now})
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, assigned_agent, started_at, created_at)
            VALUES (:id, :title, :status, :agent, :started, :created)
        """), {
            "id": "task-completed",
            "title": "Completed Task",
            "status": "in_progress",
            "agent": "agent-completed",
            "started": now,
            "created": now,
        })
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-completed/tasks/task-completed/report",
            json={
                "status": "completed",
                "result": "Task successfully completed",
                "actual_hours": 3.5,
                "quality_score": 0.95,
                "artifacts": [{"type": "file", "path": "/output/result.json"}]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-completed"
        assert data["agent_id"] == "agent-completed"
        assert data["status"] == "completed"
        assert "reported_at" in data
        assert data["actual_hours"] == 3.5
        assert data["quality_score"] == 0.95

    def test_report_task_failed(self, client, test_db):
        """上报任务失败"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, current_tasks, created_at)
            VALUES (:id, :name, :status, :current, :created)
        """), {"id": "agent-failed", "name": "Failed Agent", "status": "online", "current": 1, "created": now})
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, assigned_agent, created_at)
            VALUES (:id, :title, :status, :agent, :created)
        """), {"id": "task-failed", "title": "Failed Task", "status": "in_progress", "agent": "agent-failed", "created": now})
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-failed/tasks/task-failed/report",
            json={
                "status": "failed",
                "error_message": "Connection timeout",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"

    def test_report_task_partial(self, client, test_db):
        """上报任务部分完成"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, current_tasks, created_at)
            VALUES (:id, :name, :status, :current, :created)
        """), {"id": "agent-partial", "name": "Partial Agent", "status": "online", "current": 1, "created": now})
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, assigned_agent, created_at)
            VALUES (:id, :title, :status, :agent, :created)
        """), {"id": "task-partial", "title": "Partial Task", "status": "in_progress", "agent": "agent-partial", "created": now})
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-partial/tasks/task-partial/report",
            json={
                "status": "partial",
                "result": "Partially completed",
            }
        )
        assert response.status_code == 200
        data = response.json()
        # partial 状态转为 failed
        assert data["status"] == "failed"

    def test_report_task_updates_agent_current_tasks(self, client, test_db):
        """上报后更新 Agent 当前任务数"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, current_tasks, created_at)
            VALUES (:id, :name, :status, :current, :created)
        """), {"id": "agent-update-report", "name": "Update Report Agent", "status": "online", "current": 2, "created": now})
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, assigned_agent, created_at)
            VALUES (:id, :title, :status, :agent, :created)
        """), {"id": "task-update-report", "title": "Update Report Task", "status": "in_progress", "agent": "agent-update-report", "created": now})
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-update-report/tasks/task-update-report/report",
            json={"status": "completed"}
        )
        assert response.status_code == 200

        # 验证 current_tasks 已减少
        row = test_db.execute(
            text("SELECT current_tasks FROM agents WHERE id = :id"),
            {"id": "agent-update-report"}
        ).fetchone()
        assert row[0] == 1

    def test_report_task_creates_execution_log(self, client, test_db):
        """上报任务创建执行日志"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, current_tasks, created_at)
            VALUES (:id, :name, :status, :current, :created)
        """), {"id": "agent-exec-log", "name": "Exec Log Agent", "status": "online", "current": 1, "created": now})
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, assigned_agent, started_at, created_at)
            VALUES (:id, :title, :status, :agent, :started, :created)
        """), {
            "id": "task-exec-log",
            "title": "Exec Log Task",
            "status": "in_progress",
            "agent": "agent-exec-log",
            "started": now,
            "created": now,
        })
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-exec-log/tasks/task-exec-log/report",
            json={
                "status": "completed",
                "result": "Execution completed",
                "quality_score": 0.9,
            }
        )
        assert response.status_code == 200

        # 验证执行日志存在
        log = test_db.execute(
            text("SELECT task_id, agent_id, action, status, output FROM execution_logs WHERE task_id = :id"),
            {"id": "task-exec-log"}
        ).fetchone()
        assert log is not None
        assert log[0] == "task-exec-log"
        assert log[1] == "agent-exec-log"
        assert log[2] == "task_complete"
        assert log[3] == "completed"

    def test_report_task_creates_activity_log(self, client, test_db):
        """上报任务创建活动日志"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, current_tasks, created_at)
            VALUES (:id, :name, :status, :current, :created)
        """), {"id": "agent-act-log", "name": "Act Log Agent", "status": "online", "current": 1, "created": now})
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, assigned_agent, created_at)
            VALUES (:id, :title, :status, :agent, :created)
        """), {"id": "task-act-log", "title": "Act Log Task", "status": "in_progress", "agent": "agent-act-log", "created": now})
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-act-log/tasks/task-act-log/report",
            json={"status": "completed"}
        )
        assert response.status_code == 200

        # 验证活动日志存在
        log = test_db.execute(
            text("SELECT task_id, new_status, actor FROM task_activity_log WHERE task_id = :id"),
            {"id": "task-act-log"}
        ).fetchone()
        assert log is not None
        assert log[0] == "task-act-log"
        assert log[1] == "reported"
        assert log[2] == "agent-act-log"

    def test_report_task_calculates_actual_hours(self, client, test_db):
        """未提供 actual_hours 时自动计算"""
        start_time = datetime.now() - timedelta(hours=2)
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, current_tasks, created_at)
            VALUES (:id, :name, :status, :current, :created)
        """), {"id": "agent-calc-hours", "name": "Calc Hours Agent", "status": "online", "current": 1, "created": now})
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, assigned_agent, started_at, created_at)
            VALUES (:id, :title, :status, :agent, :started, :created)
        """), {
            "id": "task-calc-hours",
            "title": "Calc Hours Task",
            "status": "in_progress",
            "agent": "agent-calc-hours",
            "started": start_time.isoformat(),
            "created": now,
        })
        test_db.commit()

        response = client.post(
            "/api/v1/agents/agent-calc-hours/tasks/task-calc-hours/report",
            json={"status": "completed"}
        )
        assert response.status_code == 200
        # actual_hours 应接近 2.0
        actual_hours = response.json()["actual_hours"]
        assert actual_hours is not None
        assert 1.9 <= actual_hours <= 2.1