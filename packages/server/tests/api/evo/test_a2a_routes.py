"""
L4-API-E-004 A2A (Agent-to-Agent) API 测试

对照文档：docs/09-系统设计/25-测试用例总览.md → TC-API-E-004

覆盖用例：
- TC-API-E-004: Agent 间消息广播与传递
  - POST /api/v1/a2a/broadcast — Agent 广播
  - GET /api/v1/a2a/messages — 消息列表
  - POST /api/v1/a2a/messages — 发送消息
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
    """Create TestClient with in-memory SQLite and a2a router"""
    db_config = DatabaseConfig(provider="sqlite", path=":memory:")
    db_manager = DatabaseManager(db_config)
    db_manager._engine = test_db.get_bind()
    set_db_manager(db_manager)

    from evo.api.a2a_routes import router as a2a_router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(a2a_router)
    with TestClient(app) as tc:
        yield tc


@pytest.fixture
def agents_in_db(test_db):
    """Insert test agents into DB and return their IDs"""
    agent_a = f"agent-a-{uuid.uuid4().hex[:6]}"
    agent_b = f"agent-b-{uuid.uuid4().hex[:6]}"
    agent_c = f"agent-c-{uuid.uuid4().hex[:6]}"
    now = datetime.now().isoformat()

    test_db.execute(text("""
        INSERT INTO agents (id, name, status, created_at)
        VALUES (:id, :name, :status, :created)
    """), {"id": agent_a, "name": "Agent A", "status": "online", "created": now})
    test_db.execute(text("""
        INSERT INTO agents (id, name, status, created_at)
        VALUES (:id, :name, :status, :created)
    """), {"id": agent_b, "name": "Agent B", "status": "online", "created": now})
    test_db.execute(text("""
        INSERT INTO agents (id, name, status, created_at)
        VALUES (:id, :name, :status, :created)
    """), {"id": agent_c, "name": "Agent C", "status": "offline", "created": now})
    test_db.commit()
    return {"agent_a": agent_a, "agent_b": agent_b, "agent_c": agent_c}


# ===========================================================================
# TC-API-E-004: Agent 间消息广播与传递
# ===========================================================================

class TestBroadcast:
    """TC-API-E-004-01: POST /api/v1/a2a/broadcast — Agent 广播"""

    def test_broadcast_to_all_online(self, client, test_db, agents_in_db):
        """广播给所有在线 Agent"""
        response = client.post("/api/v1/a2a/broadcast", json={
            "source_agent_id": agents_in_db["agent_a"],
            "message": "系统通知：即将进行维护",
            "channel": "system",
            "priority": "high",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["broadcast_id"] is not None
        # 只有 agent_b 在线（排除自己 agent_a，agent_c 离线）
        assert data["delivered_count"] == 1
        assert agents_in_db["agent_b"] in data["target_agents"]

    def test_broadcast_to_specific_agents(self, client, test_db, agents_in_db):
        """广播给指定的 Agent"""
        response = client.post("/api/v1/a2a/broadcast", json={
            "source_agent_id": agents_in_db["agent_a"],
            "message": "定向通知",
            "target_agents": [agents_in_db["agent_b"], agents_in_db["agent_c"]],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["delivered_count"] == 2
        assert agents_in_db["agent_b"] in data["target_agents"]
        assert agents_in_db["agent_c"] in data["target_agents"]

        # 验证消息已持久化
        rows = test_db.execute(text("""
            SELECT target_agent_id FROM a2a_messages WHERE broadcast_id = :bid
        """), {"bid": data["broadcast_id"]}).fetchall()
        target_ids = [r[0] for r in rows]
        assert agents_in_db["agent_b"] in target_ids
        assert agents_in_db["agent_c"] in target_ids

    def test_broadcast_source_not_found(self, client):
        """源 Agent 不存在时返回 404"""
        response = client.post("/api/v1/a2a/broadcast", json={
            "source_agent_id": "nonexistent-agent",
            "message": "test",
        })
        assert response.status_code == 404
        assert "Source agent not found" in response.json()["detail"]

    def test_broadcast_no_targets(self, client, test_db):
        """无目标 Agent 时返回 0 delivered"""
        # 只创建一个 Agent，广播给所有在线 Agent 会排除自己
        agent_id = f"agent-alone-{uuid.uuid4().hex[:6]}"
        test_db.execute(text("""
            INSERT INTO agents (id, name, status) VALUES (:id, :name, 'online')
        """), {"id": agent_id, "name": "Alone"})
        test_db.commit()

        response = client.post("/api/v1/a2a/broadcast", json={
            "source_agent_id": agent_id,
            "message": "没人能收到",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["delivered_count"] == 0
        assert "No target agents" in data["message"]

    def test_broadcast_message_persisted(self, client, test_db, agents_in_db):
        """广播消息正确持久化到 a2a_messages 表"""
        response = client.post("/api/v1/a2a/broadcast", json={
            "source_agent_id": agents_in_db["agent_a"],
            "message": "持久化测试",
            "target_agents": [agents_in_db["agent_b"]],
            "metadata": {"key": "value"},
            "requires_ack": True,
        })
        assert response.status_code == 200

        row = test_db.execute(text("""
            SELECT source_agent_id, target_agent_id, message, metadata, requires_ack, status
            FROM a2a_messages WHERE broadcast_id = :bid
        """), {"bid": response.json()["broadcast_id"]}).fetchone()
        assert row is not None
        assert row[0] == agents_in_db["agent_a"]
        assert row[1] == agents_in_db["agent_b"]
        assert row[2] == "持久化测试"
        assert json.loads(row[3]) == {"key": "value"}
        assert row[4] == 1
        assert row[5] == "pending"


class TestMessagesList:
    """TC-API-E-004-02: GET /api/v1/a2a/messages — 消息列表"""

    def test_list_messages_empty(self, client):
        """空数据库返回空列表"""
        response = client.get("/api/v1/a2a/messages")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_messages_with_data(self, client, test_db, agents_in_db):
        """列表返回已创建的消息"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO a2a_messages (id, source_agent_id, target_agent_id, message, channel, status, created_at)
            VALUES (:id, :source, :target, :message, :channel, :status, :created)
        """), {
            "id": f"a2a-{uuid.uuid4().hex[:8]}",
            "source": agents_in_db["agent_a"],
            "target": agents_in_db["agent_b"],
            "message": "测试消息",
            "channel": "default",
            "status": "pending",
            "created": now,
        })
        test_db.commit()

        response = client.get("/api/v1/a2a/messages")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["message"] == "测试消息"

    def test_list_messages_filter_by_target_agent(self, client, test_db, agents_in_db):
        """按 target_agent_id 过滤"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO a2a_messages (id, source_agent_id, target_agent_id, message, created_at)
            VALUES (:id, :source, :target, :message, :created)
        """), {
            "id": f"a2a-{uuid.uuid4().hex[:8]}",
            "source": agents_in_db["agent_a"],
            "target": agents_in_db["agent_b"],
            "message": "给 B 的消息",
            "created": now,
        })
        test_db.execute(text("""
            INSERT INTO a2a_messages (id, source_agent_id, target_agent_id, message, created_at)
            VALUES (:id, :source, :target, :message, :created)
        """), {
            "id": f"a2a-{uuid.uuid4().hex[:8]}",
            "source": agents_in_db["agent_a"],
            "target": agents_in_db["agent_c"],
            "message": "给 C 的消息",
            "created": now,
        })
        test_db.commit()

        response = client.get(f"/api/v1/a2a/messages?target_agent_id={agents_in_db['agent_b']}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["target_agent_id"] == agents_in_db["agent_b"]

    def test_list_messages_filter_by_source_agent(self, client, test_db, agents_in_db):
        """按 source_agent_id 过滤"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO a2a_messages (id, source_agent_id, target_agent_id, message, created_at)
            VALUES (:id, :source, :target, :message, :created)
        """), {
            "id": f"a2a-{uuid.uuid4().hex[:8]}",
            "source": agents_in_db["agent_a"],
            "target": agents_in_db["agent_b"],
            "message": "来自 A",
            "created": now,
        })
        test_db.execute(text("""
            INSERT INTO a2a_messages (id, source_agent_id, target_agent_id, message, created_at)
            VALUES (:id, :source, :target, :message, :created)
        """), {
            "id": f"a2a-{uuid.uuid4().hex[:8]}",
            "source": agents_in_db["agent_b"],
            "target": agents_in_db["agent_a"],
            "message": "来自 B",
            "created": now,
        })
        test_db.commit()

        response = client.get(f"/api/v1/a2a/messages?source_agent_id={agents_in_db['agent_a']}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["source_agent_id"] == agents_in_db["agent_a"]

    def test_list_messages_filter_by_channel(self, client, test_db, agents_in_db):
        """按 channel 过滤"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO a2a_messages (id, source_agent_id, target_agent_id, message, channel, created_at)
            VALUES (:id, :source, :target, :message, :channel, :created)
        """), {
            "id": f"a2a-{uuid.uuid4().hex[:8]}",
            "source": agents_in_db["agent_a"],
            "target": agents_in_db["agent_b"],
            "message": "系统消息",
            "channel": "system",
            "created": now,
        })
        test_db.execute(text("""
            INSERT INTO a2a_messages (id, source_agent_id, target_agent_id, message, channel, created_at)
            VALUES (:id, :source, :target, :message, :channel, :created)
        """), {
            "id": f"a2a-{uuid.uuid4().hex[:8]}",
            "source": agents_in_db["agent_a"],
            "target": agents_in_db["agent_b"],
            "message": "默认消息",
            "channel": "default",
            "created": now,
        })
        test_db.commit()

        response = client.get("/api/v1/a2a/messages?channel=system")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    def test_list_messages_filter_by_status(self, client, test_db, agents_in_db):
        """按 status 过滤"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO a2a_messages (id, source_agent_id, target_agent_id, message, status, created_at)
            VALUES (:id, :source, :target, :message, :status, :created)
        """), {
            "id": f"a2a-{uuid.uuid4().hex[:8]}",
            "source": agents_in_db["agent_a"],
            "target": agents_in_db["agent_b"],
            "message": "待处理",
            "status": "pending",
            "created": now,
        })
        test_db.execute(text("""
            INSERT INTO a2a_messages (id, source_agent_id, target_agent_id, message, status, created_at)
            VALUES (:id, :source, :target, :message, :status, :created)
        """), {
            "id": f"a2a-{uuid.uuid4().hex[:8]}",
            "source": agents_in_db["agent_a"],
            "target": agents_in_db["agent_b"],
            "message": "已处理",
            "status": "processed",
            "created": now,
        })
        test_db.commit()

        response = client.get("/api/v1/a2a/messages?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "pending"

    def test_list_messages_filter_by_agent_id(self, client, test_db, agents_in_db):
        """按 agent_id 过滤（源或目标）"""
        now = datetime.now().isoformat()
        # Agent A 发送给 Agent B
        test_db.execute(text("""
            INSERT INTO a2a_messages (id, source_agent_id, target_agent_id, message, created_at)
            VALUES (:id, :source, :target, :message, :created)
        """), {
            "id": f"a2a-{uuid.uuid4().hex[:8]}",
            "source": agents_in_db["agent_a"],
            "target": agents_in_db["agent_b"],
            "message": "A->B",
            "created": now,
        })
        # Agent B 发送给 Agent C
        test_db.execute(text("""
            INSERT INTO a2a_messages (id, source_agent_id, target_agent_id, message, created_at)
            VALUES (:id, :source, :target, :message, :created)
        """), {
            "id": f"a2a-{uuid.uuid4().hex[:8]}",
            "source": agents_in_db["agent_b"],
            "target": agents_in_db["agent_c"],
            "message": "B->C",
            "created": now,
        })
        test_db.commit()

        response = client.get(f"/api/v1/a2a/messages?agent_id={agents_in_db['agent_b']}")
        assert response.status_code == 200
        data = response.json()
        # Agent B 既作为源也作为目标
        assert data["total"] == 2

    def test_list_messages_pagination(self, client, test_db, agents_in_db):
        """分页查询"""
        now = datetime.now().isoformat()
        for i in range(5):
            test_db.execute(text("""
                INSERT INTO a2a_messages (id, source_agent_id, target_agent_id, message, created_at)
                VALUES (:id, :source, :target, :message, :created)
            """), {
                "id": f"a2a-{i:04d}",
                "source": agents_in_db["agent_a"],
                "target": agents_in_db["agent_b"],
                "message": f"Message {i}",
                "created": now,
            })
        test_db.commit()

        response = client.get("/api/v1/a2a/messages?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2


class TestMessagesCreate:
    """TC-API-E-004-03: POST /api/v1/a2a/messages — 发送消息"""

    def test_create_message_success(self, client, test_db, agents_in_db):
        """成功创建 A2A 消息"""
        response = client.post("/api/v1/a2a/messages", json={
            "source_agent_id": agents_in_db["agent_a"],
            "target_agent_id": agents_in_db["agent_b"],
            "message": "Hello from A to B",
            "channel": "chat",
            "priority": "normal",
            "metadata": {"type": "greeting"},
            "requires_ack": False,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["id"].startswith("a2a-")
        assert data["source_agent_id"] == agents_in_db["agent_a"]
        assert data["target_agent_id"] == agents_in_db["agent_b"]
        assert data["message"] == "Hello from A to B"
        assert data["channel"] == "chat"
        assert data["status"] == "pending"
        assert data["metadata"] == {"type": "greeting"}

    def test_create_message_minimal(self, client, test_db, agents_in_db):
        """最少字段创建消息"""
        response = client.post("/api/v1/a2a/messages", json={
            "source_agent_id": agents_in_db["agent_a"],
            "target_agent_id": agents_in_db["agent_b"],
            "message": "Minimal message",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["id"].startswith("a2a-")
        assert data["channel"] == "default"
        assert data["priority"] == "normal"
        assert data["status"] == "pending"

    def test_create_message_source_not_found(self, client, test_db, agents_in_db):
        """源 Agent 不存在时返回 404"""
        response = client.post("/api/v1/a2a/messages", json={
            "source_agent_id": "nonexistent-source",
            "target_agent_id": agents_in_db["agent_b"],
            "message": "test",
        })
        assert response.status_code == 404
        assert "Source agent not found" in response.json()["detail"]

    def test_create_message_target_not_found(self, client, test_db, agents_in_db):
        """目标 Agent 不存在时返回 404"""
        response = client.post("/api/v1/a2a/messages", json={
            "source_agent_id": agents_in_db["agent_a"],
            "target_agent_id": "nonexistent-target",
            "message": "test",
        })
        assert response.status_code == 404
        assert "Target agent not found" in response.json()["detail"]

    def test_create_message_verify_persisted(self, client, test_db, agents_in_db):
        """创建的消息已持久化到数据库"""
        response = client.post("/api/v1/a2a/messages", json={
            "source_agent_id": agents_in_db["agent_a"],
            "target_agent_id": agents_in_db["agent_b"],
            "message": "Persistence test",
            "requires_ack": True,
        })
        assert response.status_code == 200
        message_id = response.json()["id"]

        row = test_db.execute(text("""
            SELECT id, source_agent_id, target_agent_id, message, requires_ack, status
            FROM a2a_messages WHERE id = :id
        """), {"id": message_id}).fetchone()
        assert row is not None
        assert row[0] == message_id
        assert row[1] == agents_in_db["agent_a"]
        assert row[2] == agents_in_db["agent_b"]
        assert row[3] == "Persistence test"
        assert row[4] == 1
        assert row[5] == "pending"
