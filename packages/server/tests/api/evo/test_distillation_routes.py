"""
L4-API-E-002 Distillation API 测试

对照文档：docs/09-系统设计/25-测试用例总览.md → TC-API-E-002

覆盖用例：
- TC-API-E-002: 经验蒸馏 / Capsule 固化 / 能力进化
  - POST /api/v1/evo/distill — 经验蒸馏（mock RuleDistiller）
  - POST /api/v1/evo/solidify — Capsule 固化
  - POST /api/v1/evo/evolve-capabilities — 能力进化
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
    """Create TestClient with in-memory SQLite and distillation router"""
    db_config = DatabaseConfig(provider="sqlite", path=":memory:")
    db_manager = DatabaseManager(db_config)
    db_manager._engine = test_db.get_bind()
    set_db_manager(db_manager)

    from evo.api.distillation_routes import router as distill_router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(distill_router)
    with TestClient(app) as tc:
        yield tc


@pytest.fixture
def sample_gene_in_db(test_db):
    """Insert a gene into DB and return its ID"""
    gene_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    test_db.execute(text("""
        INSERT INTO genes (id, schema_version, category, signals_match, strategy, created_at, updated_at)
        VALUES (:id, '1.0', 'capability', :signals, :strategy, :created, :updated)
    """), {
        "id": gene_id,
        "signals": json.dumps(["task_completed"]),
        "strategy": json.dumps([{"step": "analyze"}]),
        "created": now,
        "updated": now,
    })
    test_db.commit()
    return gene_id


# ===========================================================================
# TC-API-E-002: 经验蒸馏 / Capsule 固化 / 能力进化
# ===========================================================================

class TestDistillExperience:
    """TC-API-E-002-01: POST /api/v1/evo/distill — 经验蒸馏（mock RuleDistiller）"""

    @patch("evo.api.distillation_routes.RuleDistiller")
    def test_distill_with_task_ids(self, mock_distiller_class, client, test_db):
        """指定 task_ids 进行蒸馏"""
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        test_db.execute(text("""
            INSERT INTO tasks (id, title, category, assigned_agent, status, result, created_at)
            VALUES (:id, :title, :cat, :agent, :status, :result, :created)
        """), {
            "id": task_id,
            "title": "数据处理",
            "cat": "data",
            "agent": "agent-1",
            "status": "completed",
            "result": json.dumps({"method": "pandas"}),
            "created": datetime.now().isoformat(),
        })
        test_db.commit()

        mock_distiller = MagicMock()
        mock_distiller_class.return_value = mock_distiller

        mock_gene = MagicMock()
        mock_gene.id = str(uuid.uuid4())
        mock_gene.category = "capability"
        mock_gene.schema_version = "1.0"
        mock_gene.signals_match = []
        mock_gene.preconditions = []
        mock_gene.strategy = []
        mock_gene.constraints = {}
        mock_gene.validation = []
        mock_gene.epigenetic_marks = []
        mock_gene.asset_id = None
        mock_distiller.distill.return_value = [mock_gene]

        response = client.post("/api/v1/evo/distill", json={
            "task_ids": [task_id],
            "min_support": 1,
            "min_confidence": 0.3,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["genes_extracted"] == 1
        assert data["source_tasks"] == 1
        assert len(data["gene_ids"]) == 1

    @patch("evo.api.distillation_routes.RuleDistiller")
    def test_distill_no_tasks(self, mock_distiller_class, client):
        """无任务记录时返回空结果"""
        mock_distiller = MagicMock()
        mock_distiller_class.return_value = mock_distiller
        mock_distiller.distill.return_value = []

        response = client.post("/api/v1/evo/distill", json={
            "min_support": 2,
            "min_confidence": 0.5,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["genes_extracted"] == 0
        assert "No task records" in data["message"]

    @patch("evo.api.distillation_routes.RuleDistiller")
    def test_distill_persists_genes(self, mock_distiller_class, client, test_db):
        """蒸馏后将 Gene 持久化到数据库"""
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        test_db.execute(text("""
            INSERT INTO tasks (id, title, status, created_at)
            VALUES (:id, :title, :status, :created)
        """), {
            "id": task_id,
            "title": "Test Task",
            "status": "completed",
            "created": datetime.now().isoformat(),
        })
        test_db.commit()

        mock_distiller = MagicMock()
        mock_distiller_class.return_value = mock_distiller

        mock_gene = MagicMock()
        mock_gene.id = str(uuid.uuid4())
        mock_gene.category = "pattern"
        mock_gene.schema_version = "1.0"
        mock_gene.signals_match = []
        mock_gene.preconditions = []
        mock_gene.strategy = []
        mock_gene.constraints = {}
        mock_gene.validation = []
        mock_gene.epigenetic_marks = []
        mock_gene.asset_id = None
        mock_distiller.distill.return_value = [mock_gene]

        client.post("/api/v1/evo/distill", json={"task_ids": [task_id]})

        row = test_db.execute(text("SELECT id, category FROM genes WHERE id = :id"), {"id": mock_gene.id}).fetchone()
        assert row is not None
        assert row[1] == "pattern"


class TestSolidifyCapsule:
    """TC-API-E-002-02: POST /api/v1/evo/solidify — Capsule 固化"""

    def test_solidify_success(self, client, test_db, sample_gene_in_db):
        """成功将 Gene 固化为 Capsule"""
        response = client.post("/api/v1/evo/solidify", json={
            "gene_id": sample_gene_in_db,
            "summary": "数据处理最佳实践",
            "content": '{"method": "pandas"}',
            "trigger": ["task_completed"],
            "strategy": [{"step": "apply"}],
            "confidence": 0.85,
            "blast_radius": {"scope": "module"},
        })
        assert response.status_code == 200
        data = response.json()
        assert data["capsule_id"] is not None
        assert data["gene_id"] == sample_gene_in_db
        assert data["status"] == "draft"

        # 验证 Capsule 已持久化
        capsule_row = test_db.execute(text(
            "SELECT id, gene_id, summary, confidence FROM capsules WHERE id = :id"
        ), {"id": data["capsule_id"]}).fetchone()
        assert capsule_row is not None
        assert capsule_row[1] == sample_gene_in_db
        assert capsule_row[2] == "数据处理最佳实践"
        assert capsule_row[3] == 0.85

    def test_solidify_gene_not_found(self, client):
        """Gene 不存在时返回 404"""
        response = client.post("/api/v1/evo/solidify", json={
            "gene_id": "nonexistent-gene",
            "summary": "test",
        })
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_solidify_minimal(self, client, test_db, sample_gene_in_db):
        """最少字段固化 Capsule"""
        response = client.post("/api/v1/evo/solidify", json={
            "gene_id": sample_gene_in_db,
            "summary": "最小 Capsule",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["capsule_id"] is not None
        assert data["status"] == "draft"


class TestEvolveCapabilities:
    """TC-API-E-002-03: POST /api/v1/evo/evolve-capabilities — 能力进化"""

    def test_evolve_with_gene_ids(self, client, test_db):
        """指定 gene_ids 进行能力进化"""
        gene_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO genes (id, category, strategy, constraints, created_at, updated_at)
            VALUES (:id, 'capability', :strategy, :constraints, :created, :updated)
        """), {
            "id": gene_id,
            "strategy": json.dumps([{"step": "evolve"}]),
            "constraints": json.dumps({"max_retries": 3}),
            "created": now,
            "updated": now,
        })
        test_db.commit()

        response = client.post("/api/v1/evo/evolve-capabilities", json={
            "gene_ids": [gene_id],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["evolved_count"] == 1
        assert len(data["capabilities"]) == 1
        assert data["capabilities"][0]["gene_id"] == gene_id
        assert data["capabilities"][0]["category"] == "capability"

    def test_evolve_no_genes(self, client):
        """无 Gene 时返回空列表"""
        response = client.post("/api/v1/evo/evolve-capabilities", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["evolved_count"] == 0
        assert data["capabilities"] == []

    def test_evolve_with_agent_id(self, client, test_db):
        """指定 agent_id 进行进化并更新 capability_tags"""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        test_db.execute(text("""
            INSERT INTO agents (id, name, status, created_at)
            VALUES (:id, :name, 'online', :created)
        """), {
            "id": agent_id,
            "name": "Test Agent",
            "created": datetime.now().isoformat(),
        })
        gene_id = str(uuid.uuid4())
        test_db.execute(text("""
            INSERT INTO genes (id, category, strategy, constraints, created_at, updated_at)
            VALUES (:id, 'capability', :strategy, :constraints, :created, :updated)
        """), {
            "id": gene_id,
            "strategy": json.dumps([{"step": "evolve"}]),
            "constraints": json.dumps({}),
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
        })
        test_db.commit()

        response = client.post("/api/v1/evo/evolve-capabilities", json={
            "agent_id": agent_id,
            "gene_ids": [gene_id],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == agent_id
        assert data["evolved_count"] == 1

        # 验证 Agent 的 capability_tags 已更新
        agent_row = test_db.execute(text(
            "SELECT capability_tags FROM agents WHERE id = :id"
        ), {"id": agent_id}).fetchone()
        assert agent_row is not None
        tags = json.loads(agent_row[0])
        assert "evolved_at" in tags
        assert tags["gene_count"] == 1

    def test_evolve_agent_not_found(self, client, test_db):
        """agent_id 指定但 Agent 不存在时返回 404"""
        test_db.execute(text("""
            INSERT INTO agents (id, name, status) VALUES ('nonexistent', 'ghost', 'offline')
        """))
        test_db.commit()

        # 需要先确保 genes 表中有数据才能走到 agent 查询分支
        # 不指定 gene_ids 且指定 agent_id 时会查 agents 表
        response = client.post("/api/v1/evo/evolve-capabilities", json={
            "agent_id": "totally-nonexistent-agent",
        })
        assert response.status_code == 404
        assert "Agent not found" in response.json()["detail"]
