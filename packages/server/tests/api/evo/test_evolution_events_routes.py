"""
L4-API-E-003 Evolution Events API 测试

对照文档：docs/09-系统设计/25-测试用例总览.md → TC-API-E-003

覆盖用例：
- TC-API-E-003: 进化事件管理与回滚
  - GET /api/v1/evo/evolution-events — 事件列表
  - POST /api/v1/evo/evolution-events — 创建事件
  - POST /api/v1/evo/evolution-events/{event_id}/revert — 事件回滚
"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

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
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS genes (
                id TEXT PRIMARY KEY,
                schema_version TEXT DEFAULT '1.0',
                category TEXT,
                signals_match TEXT,
                preconditions TEXT,
                strategy TEXT,
                constraints TEXT,
                validation TEXT,
                epigenetic_marks TEXT,
                asset_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS capsules (
                id TEXT PRIMARY KEY,
                schema_version TEXT DEFAULT '1.0',
                trigger TEXT,
                gene_id TEXT REFERENCES genes(id),
                summary TEXT,
                confidence REAL,
                blast_radius TEXT,
                outcome TEXT,
                success_streak INT DEFAULT 0,
                content TEXT,
                diff TEXT,
                strategy TEXT,
                a2a TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS evolution_events (
                id TEXT PRIMARY KEY,
                schema_version TEXT DEFAULT '1.0',
                parent_id TEXT,
                intent TEXT,
                signals TEXT,
                genes_used TEXT,
                mutation_id TEXT,
                blast_radius TEXT,
                outcome TEXT,
                capsule_id TEXT,
                env_fingerprint TEXT,
                meta TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT,
                status TEXT DEFAULT 'offline',
                capabilities TEXT,
                capability_tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                goal_id TEXT,
                title TEXT,
                category TEXT,
                assigned_agent TEXT,
                status TEXT DEFAULT 'todo',
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS a2a_messages (
                id TEXT PRIMARY KEY,
                broadcast_id TEXT,
                source_agent_id TEXT,
                target_agent_id TEXT,
                message TEXT,
                channel TEXT DEFAULT 'default',
                priority TEXT DEFAULT 'normal',
                status TEXT DEFAULT 'pending',
                metadata TEXT,
                requires_ack INTEGER DEFAULT 0,
                ack_status TEXT,
                ack_response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivered_at TIMESTAMP,
                ack_at TIMESTAMP
            )
        """))
        conn.commit()
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture
def client(test_db):
    """Create TestClient with in-memory SQLite and evolution_events router"""
    db_config = DatabaseConfig(provider="sqlite", path=":memory:")
    db_manager = DatabaseManager(db_config)
    db_manager._engine = test_db.get_bind()
    set_db_manager(db_manager)

    from evo.api.evolution_events_routes import router as events_router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(events_router)
    with TestClient(app) as tc:
        yield tc


# ===========================================================================
# TC-API-E-003: 进化事件管理与回滚
# ===========================================================================

class TestEvolutionEventsList:
    """TC-API-E-003-01: GET /api/v1/evo/evolution-events — 事件列表"""

    def test_list_events_empty(self, client):
        """空数据库返回空列表"""
        response = client.get("/api/v1/evo/evolution-events")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_events_with_data(self, client, test_db):
        """列表返回已创建的事件"""
        event_id = f"evt-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO evolution_events (id, schema_version, intent, signals, created_at)
            VALUES (:id, '1.0', :intent, :signals, :created)
        """), {
            "id": event_id,
            "intent": "distillation",
            "signals": json.dumps(["signal1"]),
            "created": now,
        })
        test_db.commit()

        response = client.get("/api/v1/evo/evolution-events")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == event_id
        assert data["items"][0]["intent"] == "distillation"

    def test_list_events_filter_by_intent(self, client, test_db):
        """按 intent 过滤"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO evolution_events (id, schema_version, intent, created_at)
            VALUES (:id, '1.0', :intent, :created)
        """), {"id": f"evt-{uuid.uuid4().hex[:6]}", "intent": "distillation", "created": now})
        test_db.execute(text("""
            INSERT INTO evolution_events (id, schema_version, intent, created_at)
            VALUES (:id, '1.0', :intent, :created)
        """), {"id": f"evt-{uuid.uuid4().hex[:6]}", "intent": "mutation", "created": now})
        test_db.commit()

        response = client.get("/api/v1/evo/evolution-events?intent=distillation")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["intent"] == "distillation"

    def test_list_events_filter_by_capsule_id(self, client, test_db):
        """按 capsule_id 过滤"""
        capsule_id = f"cap-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO evolution_events (id, schema_version, intent, capsule_id, created_at)
            VALUES (:id, '1.0', 'distillation', :capsule, :created)
        """), {"id": f"evt-{uuid.uuid4().hex[:6]}", "capsule": capsule_id, "created": now})
        test_db.execute(text("""
            INSERT INTO evolution_events (id, schema_version, intent, created_at)
            VALUES (:id, '1.0', 'distillation', :created)
        """), {"id": f"evt-{uuid.uuid4().hex[:6]}", "created": now})
        test_db.commit()

        response = client.get(f"/api/v1/evo/evolution-events?capsule_id={capsule_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_list_events_pagination(self, client, test_db):
        """分页查询"""
        now = datetime.now().isoformat()
        for i in range(5):
            test_db.execute(text("""
                INSERT INTO evolution_events (id, schema_version, intent, created_at)
                VALUES (:id, '1.0', :intent, :created)
            """), {
                "id": f"evt-{i:04d}",
                "intent": "distillation",
                "created": now,
            })
        test_db.commit()

        response = client.get("/api/v1/evo/evolution-events?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2

    def test_list_events_excludes_reverted(self, client, test_db):
        """已回滚的事件默认不显示"""
        now = datetime.now().isoformat()
        # 正常事件
        test_db.execute(text("""
            INSERT INTO evolution_events (id, schema_version, intent, created_at)
            VALUES (:id, '1.0', 'distillation', :created)
        """), {"id": "evt-normal", "created": now})
        # 已回滚事件
        test_db.execute(text("""
            INSERT INTO evolution_events (id, schema_version, intent, meta, created_at)
            VALUES (:id, '1.0', 'distillation', :meta, :created)
        """), {"id": "evt-reverted", "meta": json.dumps({"reverted": True}), "created": now})
        test_db.commit()

        response = client.get("/api/v1/evo/evolution-events")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == "evt-normal"


class TestEvolutionEventCreate:
    """TC-API-E-003-02: POST /api/v1/evo/evolution-events — 创建事件"""

    def test_create_event_success(self, client):
        """成功创建进化事件"""
        response = client.post("/api/v1/evo/evolution-events", json={
            "intent": "distillation",
            "signals": ["signal1", "signal2"],
            "genes_used": ["gene-1", "gene-2"],
            "mutation_id": "mut-001",
            "blast_radius": {"scope": "module"},
            "outcome": {"result": "success"},
            "capsule_id": "cap-001",
            "env_fingerprint": {"platform": "linux"},
            "meta": {"source": "test"},
        })
        assert response.status_code == 200
        data = response.json()
        assert data["id"].startswith("evt-")
        assert data["intent"] == "distillation"
        assert data["signals"] == ["signal1", "signal2"]
        assert data["genes_used"] == ["gene-1", "gene-2"]
        assert data["capsule_id"] == "cap-001"
        assert data["schema_version"] == "1.0"

    def test_create_event_minimal(self, client):
        """最少字段创建事件（仅 intent 必填）"""
        response = client.post("/api/v1/evo/evolution-events", json={
            "intent": "mutation",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["id"].startswith("evt-")
        assert data["intent"] == "mutation"
        assert data["signals"] is None
        assert data["genes_used"] is None

    def test_create_event_with_parent(self, client, test_db):
        """创建带 parent_id 的事件"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO evolution_events (id, schema_version, intent, created_at)
            VALUES ('evt-parent', '1.0', 'mutation', :created)
        """), {"created": now})
        test_db.commit()

        response = client.post("/api/v1/evo/evolution-events", json={
            "intent": "evaluation",
            "parent_id": "evt-parent",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["parent_id"] == "evt-parent"

    def test_create_event_parent_not_found(self, client):
        """parent_id 不存在时返回 400"""
        response = client.post("/api/v1/evo/evolution-events", json={
            "intent": "evaluation",
            "parent_id": "nonexistent-parent",
        })
        assert response.status_code == 400
        assert "Parent event not found" in response.json()["detail"]

    def test_create_event_verify_persisted(self, client, test_db):
        """创建的事件已持久化到数据库"""
        response = client.post("/api/v1/evo/evolution-events", json={
            "intent": "promotion",
            "outcome": {"from": "draft", "to": "validated"},
        })
        assert response.status_code == 200
        event_id = response.json()["id"]

        row = test_db.execute(text(
            "SELECT id, intent FROM evolution_events WHERE id = :id"
        ), {"id": event_id}).fetchone()
        assert row is not None
        assert row[0] == event_id
        assert row[1] == "promotion"


class TestEvolutionEventRevert:
    """TC-API-E-003-03: POST /api/v1/evo/evolution-events/{event_id}/revert — 事件回滚"""

    def test_revert_event_success(self, client, test_db):
        """成功回滚事件"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO evolution_events (id, schema_version, intent, created_at)
            VALUES (:id, '1.0', 'distillation', :created)
        """), {"id": "evt-to-revert", "created": now})
        test_db.commit()

        response = client.post("/api/v1/evo/evolution-events/evt-to-revert/revert", json={
            "reason": "测试回滚",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == "evt-to-revert"
        assert data["reverted"] is True
        assert data["reverted_at"] is not None
        assert data["reason"] == "测试回滚"
        assert data["capsule_deprecated"] is False

        # 验证 meta 已更新
        row = test_db.execute(text("SELECT meta FROM evolution_events WHERE id = :id"), {"id": "evt-to-revert"}).fetchone()
        meta = json.loads(row[0])
        assert meta["reverted"] is True
        assert meta["revert_reason"] == "测试回滚"

    def test_revert_event_without_reason(self, client, test_db):
        """不带 reason 回滚"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO evolution_events (id, schema_version, intent, created_at)
            VALUES (:id, '1.0', 'mutation', :created)
        """), {"id": "evt-revert-no-reason", "created": now})
        test_db.commit()

        response = client.post("/api/v1/evo/evolution-events/evt-revert-no-reason/revert")
        assert response.status_code == 200
        data = response.json()
        assert data["reverted"] is True
        assert data["reason"] is None

    def test_revert_event_not_found(self, client):
        """回滚不存在的事件返回 404"""
        response = client.post("/api/v1/evo/evolution-events/nonexistent/revert")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_revert_event_already_reverted(self, client, test_db):
        """重复回滚返回 400"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO evolution_events (id, schema_version, intent, meta, created_at)
            VALUES (:id, '1.0', 'distillation', :meta, :created)
        """), {
            "id": "evt-already-reverted",
            "meta": json.dumps({"reverted": True, "reverted_at": now}),
            "created": now,
        })
        test_db.commit()

        response = client.post("/api/v1/evo/evolution-events/evt-already-reverted/revert")
        assert response.status_code == 400
        assert "already reverted" in response.json()["detail"]

    def test_revert_event_with_capsule(self, client, test_db):
        """回滚关联 Capsule 的事件时，Capsule 也被标记为 deprecated"""
        now = datetime.now().isoformat()
        capsule_id = "cap-to-deprecate"
        test_db.execute(text("""
            INSERT INTO capsules (id, summary, outcome, created_at)
            VALUES (:id, :summary, :outcome, :created)
        """), {
            "id": capsule_id,
            "summary": "Test Capsule",
            "outcome": json.dumps({"status": "validated"}),
            "created": now,
        })
        test_db.execute(text("""
            INSERT INTO evolution_events (id, schema_version, intent, capsule_id, created_at)
            VALUES (:id, '1.0', 'distillation', :capsule, :created)
        """), {"id": "evt-with-capsule", "capsule": capsule_id, "created": now})
        test_db.commit()

        response = client.post("/api/v1/evo/evolution-events/evt-with-capsule/revert", json={
            "reason": "回滚并废弃 Capsule",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["capsule_deprecated"] is True

        # 验证 Capsule 已被废弃
        cap_row = test_db.execute(text(
            "SELECT outcome FROM capsules WHERE id = :id"
        ), {"id": capsule_id}).fetchone()
        cap_outcome = json.loads(cap_row[0])
        assert cap_outcome["status"] == "deprecated"
        assert cap_outcome["deprecated_by_event_revert"] == "evt-with-capsule"
