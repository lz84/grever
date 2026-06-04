"""
L4-API-V-001 Vigil Trust Routes API 测试

对照文档：docs/09-系统设计/25-测试用例总览.md → TC-API-V-001

覆盖用例：
- TC-API-V-001: Agent 信任评估管理
  - GET /api/v1/vigil/trust/agents/{agent_id} — 查询 Agent 信任评分
  - POST /api/v1/vigil/trust/agents/{agent_id} — 提交信任评估
  - GET /api/v1/vigil/trust/agents/{agent_id}/history — 查询信任历史
"""

import json
import sys
import uuid
from datetime import datetime
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
        # 基础 agents 表
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # trust_evaluations 表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trust_evaluations (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                score REAL NOT NULL,
                level TEXT NOT NULL,
                reason TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # heartbeat_logs 表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS heartbeat_logs (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                status TEXT DEFAULT 'online',
                latency_ms INTEGER,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # disputes 表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS disputes (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                involved_agents TEXT,
                status TEXT DEFAULT 'open',
                reason TEXT,
                resolution TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        """))
        conn.commit()
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture
def client(test_db):
    """Create TestClient with in-memory SQLite and trust routes"""
    db_config = DatabaseConfig(provider="sqlite", path=":memory:")
    db_manager = DatabaseManager(db_config)
    db_manager._engine = test_db.get_bind()
    set_db_manager(db_manager)

    from vigil.api.trust_routes import router as trust_router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(trust_router)
    with TestClient(app) as tc:
        yield tc


# ===========================================================================
# TC-API-V-001-01: GET /api/v1/vigil/trust/agents/{agent_id} — 查询信任评分
# ===========================================================================

class TestGetTrustScore:
    """TC-API-V-001-01: 查询 Agent 信任评分"""

    def test_get_trust_score_agent_not_found(self, client):
        """Agent 不存在返回 404"""
        response = client.get("/api/v1/vigil/trust/agents/nonexistent-agent")
        assert response.status_code == 404
        assert "Agent not found" in response.json()["detail"]

    def test_get_trust_score_success(self, client, test_db):
        """成功查询信任评分"""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, 'online', :created)
        """), {"id": agent_id, "name": "Test Agent", "created": now})
        test_db.commit()

        response = client.get(f"/api/v1/vigil/trust/agents/{agent_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == agent_id
        assert "score" in data
        assert "level" in data
        assert data["level"] in ("trusted", "neutral", "suspicious", "blocked")

    def test_get_trust_score_new_agent(self, client, test_db):
        """新 Agent 默认中立评分"""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, 'idle', :created)
        """), {"id": agent_id, "name": "New Agent", "created": now})
        test_db.commit()

        response = client.get(f"/api/v1/vigil/trust/agents/{agent_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 0.5  # 默认中立
        assert data["level"] == "neutral"
        assert data["total_evaluations"] == 0

    def test_get_trust_score_with_evaluation_history(self, client, test_db):
        """有评估历史时返回评估次数"""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, 'online', :created)
        """), {"id": agent_id, "name": "Test Agent", "created": now})
        test_db.commit()

        # 添加多个评估记录
        for i in range(3):
            test_db.execute(text("""
                INSERT INTO trust_evaluations (id, agent_id, score, level, reason, created_at)
                VALUES (:id, :agent, 0.8, 'trusted', 'test evaluation', :created)
            """), {"id": f"eval-{i}", "agent": agent_id, "created": now})
        test_db.commit()

        response = client.get(f"/api/v1/vigil/trust/agents/{agent_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total_evaluations"] == 3
        assert data["last_updated"] is not None


# ===========================================================================
# TC-API-V-001-02: POST /api/v1/vigil/trust/agents/{agent_id} — 提交信任评估
# ===========================================================================

class TestUpdateTrustScore:
    """TC-API-V-001-02: 提交信任评估"""

    def test_update_trust_score_agent_not_found(self, client):
        """Agent 不存在返回 404"""
        response = client.post(
            "/api/v1/vigil/trust/agents/nonexistent-agent",
            json={"score": 0.9, "reason": "Good performance"}
        )
        assert response.status_code == 404

    def test_update_trust_score_success(self, client, test_db):
        """成功更新信任评分"""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, 'online', :created)
        """), {"id": agent_id, "name": "Test Agent", "created": now})
        test_db.commit()

        response = client.post(
            f"/api/v1/vigil/trust/agents/{agent_id}",
            json={"score": 0.85, "reason": "Excellent task completion", "category": "task_completion"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == agent_id
        assert data["score"] == 0.85
        assert data["level"] == "trusted"
        assert "evaluation_id" in data
        assert "updated_at" in data

    def test_update_trust_score_invalid_score_range(self, client, test_db):
        """评分超出范围返回 400"""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, 'online', :created)
        """), {"id": agent_id, "name": "Test Agent", "created": now})
        test_db.commit()

        # 分数大于 1
        response = client.post(
            f"/api/v1/vigil/trust/agents/{agent_id}",
            json={"score": 1.5}
        )
        assert response.status_code == 400
        assert "between 0 and 1" in response.json()["detail"]

        # 分数小于 0
        response = client.post(
            f"/api/v1/vigil/trust/agents/{agent_id}",
            json={"score": -0.1}
        )
        assert response.status_code == 400

    def test_update_trust_score_persisted(self, client, test_db):
        """评估记录已持久化"""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, 'online', :created)
        """), {"id": agent_id, "name": "Test Agent", "created": now})
        test_db.commit()

        response = client.post(
            f"/api/v1/vigil/trust/agents/{agent_id}",
            json={"score": 0.7, "reason": "Stable performance", "category": "communication"}
        )
        assert response.status_code == 200
        eval_id = response.json()["evaluation_id"]

        # 验证数据库中记录存在
        row = test_db.execute(
            text("SELECT agent_id, score, level, reason, category FROM trust_evaluations WHERE id = :id"),
            {"id": eval_id}
        ).fetchone()
        assert row is not None
        assert row[0] == agent_id
        assert row[1] == 0.7
        assert row[3] == "Stable performance"
        assert row[4] == "communication"

    def test_update_trust_score_all_levels(self, client, test_db):
        """测试所有信任等级"""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, 'online', :created)
        """), {"id": agent_id, "name": "Test Agent", "created": now})
        test_db.commit()

        # trusted: >= 0.8
        response = client.post(
            f"/api/v1/vigil/trust/agents/{agent_id}",
            json={"score": 0.9}
        )
        assert response.status_code == 200
        assert response.json()["level"] == "trusted"

        # neutral: 0.4-0.8
        response = client.post(
            f"/api/v1/vigil/trust/agents/{agent_id}",
            json={"score": 0.6}
        )
        assert response.status_code == 200
        assert response.json()["level"] == "neutral"

        # suspicious: 0.2-0.4
        response = client.post(
            f"/api/v1/vigil/trust/agents/{agent_id}",
            json={"score": 0.3}
        )
        assert response.status_code == 200
        assert response.json()["level"] == "suspicious"

        # blocked: < 0.2
        response = client.post(
            f"/api/v1/vigil/trust/agents/{agent_id}",
            json={"score": 0.1}
        )
        assert response.status_code == 200
        assert response.json()["level"] == "blocked"


# ===========================================================================
# TC-API-V-001-03: GET /api/v1/vigil/trust/agents/{agent_id}/history — 信任历史
# ===========================================================================

class TestGetTrustHistory:
    """TC-API-V-001-03: 查询信任历史"""

    def test_get_trust_history_agent_not_found(self, client):
        """Agent 不存在返回 404"""
        response = client.get("/api/v1/vigil/trust/agents/nonexistent-agent/history")
        assert response.status_code == 404

    def test_get_trust_history_empty(self, client, test_db):
        """空历史返回空列表"""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, 'online', :created)
        """), {"id": agent_id, "name": "Test Agent", "created": now})
        test_db.commit()

        response = client.get(f"/api/v1/vigil/trust/agents/{agent_id}/history")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == agent_id
        assert data["history"] == []
        assert data["total_records"] == 0

    def test_get_trust_history_with_records(self, client, test_db):
        """返回历史记录列表"""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, 'online', :created)
        """), {"id": agent_id, "name": "Test Agent", "created": now})
        test_db.commit()

        # 添加多条评估记录
        for i in range(3):
            test_db.execute(text("""
                INSERT INTO trust_evaluations (id, agent_id, score, level, reason, category, created_at)
                VALUES (:id, :agent, :score, :level, :reason, :cat, :created)
            """), {
                "id": f"eval-{i}",
                "agent": agent_id,
                "score": 0.8 - i * 0.1,
                "level": "trusted" if i == 0 else "neutral",
                "reason": f"Evaluation {i}",
                "cat": "task_completion" if i % 2 == 0 else "communication",
                "created": now,
            })
        test_db.commit()

        response = client.get(f"/api/v1/vigil/trust/agents/{agent_id}/history")
        assert response.status_code == 200
        data = response.json()
        assert data["total_records"] == 3
        assert len(data["history"]) == 3
        # 按时间倒序
        assert data["history"][0]["id"] == "eval-2"
        assert "current_score" in data

    def test_get_trust_history_pagination(self, client, test_db):
        """分页查询历史记录"""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, 'online', :created)
        """), {"id": agent_id, "name": "Test Agent", "created": now})
        test_db.commit()

        # 添加 10 条记录
        for i in range(10):
            test_db.execute(text("""
                INSERT INTO trust_evaluations (id, agent_id, score, level, reason, created_at)
                VALUES (:id, :agent, 0.8, 'trusted', :reason, :created)
            """), {"id": f"eval-{i:03d}", "agent": agent_id, "reason": f"Reason {i}", "created": now})
        test_db.commit()

        # limit=3, offset=0
        response = client.get(f"/api/v1/vigil/trust/agents/{agent_id}/history?limit=3&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["total_records"] == 10
        assert len(data["history"]) == 3

        # limit=3, offset=3
        response = client.get(f"/api/v1/vigil/trust/agents/{agent_id}/history?limit=3&offset=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["history"]) == 3

    def test_get_trust_history_limit_validation(self, client, test_db):
        """limit 参数验证"""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, 'online', :created)
        """), {"id": agent_id, "name": "Test Agent", "created": now})
        test_db.commit()

        # limit=0 应该被拒绝
        response = client.get(f"/api/v1/vigil/trust/agents/{agent_id}/history?limit=0")
        assert response.status_code == 422  # ValidationError

        # limit=201 超过上限
        response = client.get(f"/api/v1/vigil/trust/agents/{agent_id}/history?limit=201")
        assert response.status_code == 422

    def test_get_trust_history_fields(self, client, test_db):
        """验证返回字段完整性"""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, 'online', :created)
        """), {"id": agent_id, "name": "Test Agent", "created": now})
        test_db.commit()

        test_db.execute(text("""
            INSERT INTO trust_evaluations (id, agent_id, score, level, reason, category, created_at)
            VALUES (:id, :agent, 0.85, 'trusted', 'test reason', 'security', :created)
        """), {"id": "eval-single", "agent": agent_id, "created": now})
        test_db.commit()

        response = client.get(f"/api/v1/vigil/trust/agents/{agent_id}/history")
        assert response.status_code == 200
        data = response.json()
        record = data["history"][0]
        assert "id" in record
        assert "score" in record
        assert "level" in record
        assert "reason" in record
        assert "category" in record
        assert "created_at" in record