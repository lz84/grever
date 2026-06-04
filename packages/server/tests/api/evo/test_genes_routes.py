"""
L4-API-E-001 Genes API 测试

对照文档：docs/09-系统设计/25-测试用例总览.md → TC-API-E-001

覆盖用例：
- TC-API-E-001: Genes CRUD 与特征提取
  - GET /api/v1/evo/genes — 列表查询（支持 category/asset_id 过滤、分页）
  - GET /api/v1/evo/genes/{gene_id} — 查询单个 Gene
  - POST /api/v1/evo/genes — 创建 Gene
  - POST /api/v1/evo/genes/extract — 特征提取（mock RuleDistiller）
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
                parent_id TEXT REFERENCES evolution_events(id),
                intent TEXT,
                signals TEXT,
                genes_used TEXT,
                mutation_id TEXT,
                blast_radius TEXT,
                outcome TEXT,
                capsule_id TEXT REFERENCES capsules(id),
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
                source_agent_id TEXT NOT NULL,
                target_agent_id TEXT NOT NULL,
                message TEXT NOT NULL,
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
    """Create TestClient with in-memory SQLite and Evo routers registered"""
    db_config = DatabaseConfig(provider="sqlite", path=":memory:")
    db_manager = DatabaseManager(db_config)
    db_manager._engine = test_db.get_bind()
    set_db_manager(db_manager)

    from evo.api.genes_routes import router as genes_router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(genes_router)
    with TestClient(app) as tc:
        yield tc


@pytest.fixture
def sample_gene_data():
    """Return valid gene creation payload"""
    return {
        "category": "capability",
        "signals_match": ["task_completed", "high_quality"],
        "preconditions": ["agent_has_capability"],
        "strategy": [{"step": "analyze", "action": "match"}],
        "constraints": {"max_agents": 5},
        "validation": ["confidence > 0.7"],
        "asset_id": f"asset-{uuid.uuid4().hex[:8]}",
        "schema_version": "1.0",
    }


# ===========================================================================
# TC-API-E-001: Genes CRUD 与特征提取
# ===========================================================================

class TestGenesList:
    """TC-API-E-001-01: GET /api/v1/evo/genes — 列表查询"""

    def test_list_genes_empty(self, client):
        """空数据库返回空列表"""
        response = client.get("/api/v1/evo/genes")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_genes_with_data(self, client, test_db, sample_gene_data):
        """列表返回已创建的 Gene"""
        gene_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO genes (id, category, signals_match, strategy, created_at, updated_at)
            VALUES (:id, :category, :signals, :strategy, :created, :updated)
        """), {
            "id": gene_id,
            "category": "capability",
            "signals": json.dumps(["signal1"]),
            "strategy": json.dumps([{"step": "test"}]),
            "created": now,
            "updated": now,
        })
        test_db.commit()

        response = client.get("/api/v1/evo/genes")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == gene_id
        assert data["items"][0]["category"] == "capability"

    def test_list_genes_filter_by_category(self, client, test_db):
        """按 category 过滤"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO genes (id, category, created_at, updated_at)
            VALUES (:id, :category, :created, :updated)
        """), {"id": f"g-{uuid.uuid4().hex[:6]}", "category": "capability", "created": now, "updated": now})
        test_db.execute(text("""
            INSERT INTO genes (id, category, created_at, updated_at)
            VALUES (:id, :category, :created, :updated)
        """), {"id": f"g-{uuid.uuid4().hex[:6]}", "category": "pattern", "created": now, "updated": now})
        test_db.commit()

        response = client.get("/api/v1/evo/genes?category=capability")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["category"] == "capability"

    def test_list_genes_filter_by_asset_id(self, client, test_db):
        """按 asset_id 过滤"""
        asset_id = f"asset-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO genes (id, category, asset_id, created_at, updated_at)
            VALUES (:id, :category, :asset, :created, :updated)
        """), {"id": f"g-{uuid.uuid4().hex[:6]}", "category": "capability", "asset": asset_id, "created": now, "updated": now})
        test_db.execute(text("""
            INSERT INTO genes (id, category, asset_id, created_at, updated_at)
            VALUES (:id, :category, :asset, :created, :updated)
        """), {"id": f"g-{uuid.uuid4().hex[:6]}", "category": "capability", "asset": "other-asset", "created": now, "updated": now})
        test_db.commit()

        response = client.get(f"/api/v1/evo/genes?asset_id={asset_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["asset_id"] == asset_id

    def test_list_genes_pagination(self, client, test_db):
        """分页查询"""
        now = datetime.now().isoformat()
        for i in range(5):
            test_db.execute(text("""
                INSERT INTO genes (id, category, created_at, updated_at)
                VALUES (:id, :category, :created, :updated)
            """), {
                "id": f"g-{i:04d}",
                "category": "capability",
                "created": now,
                "updated": now,
            })
        test_db.commit()

        response = client.get("/api/v1/evo/genes?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_list_genes_invalid_category(self, client):
        """无效 category 返回 400"""
        response = client.get("/api/v1/evo/genes?category=invalid_category")
        assert response.status_code == 400
        assert "Invalid category" in response.json()["detail"]


class TestGeneDetail:
    """TC-API-E-001-02: GET /api/v1/evo/genes/{gene_id} — 查询单个 Gene"""

    def test_get_gene_success(self, client, test_db):
        """查询存在的 Gene"""
        gene_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO genes (id, category, signals_match, strategy, created_at, updated_at)
            VALUES (:id, :category, :signals, :strategy, :created, :updated)
        """), {
            "id": gene_id,
            "category": "pattern",
            "signals": json.dumps(["sig1", "sig2"]),
            "strategy": json.dumps([{"step": "test"}]),
            "created": now,
            "updated": now,
        })
        test_db.commit()

        response = client.get(f"/api/v1/evo/genes/{gene_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == gene_id
        assert data["category"] == "pattern"
        assert data["signals_match"] == ["sig1", "sig2"]
        assert data["strategy"] == [{"step": "test"}]

    def test_get_gene_not_found(self, client):
        """查询不存在的 Gene 返回 404"""
        response = client.get("/api/v1/evo/genes/nonexistent-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestGeneCreate:
    """TC-API-E-001-03: POST /api/v1/evo/genes — 创建 Gene"""

    def test_create_gene_success(self, client, sample_gene_data):
        """成功创建 Gene"""
        response = client.post("/api/v1/evo/genes", json=sample_gene_data)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None
        assert data["category"] == "capability"
        assert data["signals_match"] == ["task_completed", "high_quality"]
        assert data["preconditions"] == ["agent_has_capability"]
        assert data["strategy"] == [{"step": "analyze", "action": "match"}]
        assert data["constraints"] == {"max_agents": 5}
        assert data["asset_id"] == sample_gene_data["asset_id"]

    def test_create_gene_minimal(self, client):
        """仅必填字段创建 Gene"""
        response = client.post("/api/v1/evo/genes", json={"category": "pattern"})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None
        assert data["category"] == "pattern"
        assert data["schema_version"] == "1.0"

    def test_create_gene_invalid_category(self, client):
        """无效 category 返回 400"""
        response = client.post("/api/v1/evo/genes", json={"category": "bogus"})
        assert response.status_code == 400
        assert "Invalid category" in response.json()["detail"]

    def test_create_gene_verify_persisted(self, client, test_db, sample_gene_data):
        """创建的 Gene 已持久化到数据库"""
        response = client.post("/api/v1/evo/genes", json=sample_gene_data)
        assert response.status_code == 200
        gene_id = response.json()["id"]

        row = test_db.execute(text("SELECT id, category FROM genes WHERE id = :id"), {"id": gene_id}).fetchone()
        assert row is not None
        assert row[0] == gene_id
        assert row[1] == "capability"


class TestGeneExtract:
    """TC-API-E-001-04: POST /api/v1/evo/genes/extract — 特征提取（mock RuleDistiller）"""

    @patch("evo.api.genes_routes.RuleDistiller")
    def test_extract_genes_with_task_ids(self, mock_distiller_class, client, test_db):
        """通过指定 task_ids 进行特征提取"""
        # 创建测试任务
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        test_db.execute(text("""
            INSERT INTO tasks (id, title, category, assigned_agent, status, result, created_at)
            VALUES (:id, :title, :cat, :agent, :status, :result, :created)
        """), {
            "id": task_id,
            "title": "数据处理任务",
            "cat": "data",
            "agent": "agent-1",
            "status": "completed",
            "result": json.dumps({"method": "pandas"}),
            "created": datetime.now().isoformat(),
        })
        test_db.commit()

        # Mock RuleDistiller
        mock_distiller = MagicMock()
        mock_distiller_class.return_value = mock_distiller

        mock_gene = MagicMock()
        mock_gene.id = str(uuid.uuid4())
        mock_gene.category = "capability"
        mock_gene.schema_version = "1.0"
        mock_gene.signals_match = ["task_completed"]
        mock_gene.preconditions = []
        mock_gene.strategy = [{"step": "test"}]
        mock_gene.constraints = {}
        mock_gene.validation = []
        mock_gene.epigenetic_marks = []
        mock_gene.asset_id = None
        mock_distiller.distill.return_value = [mock_gene]

        response = client.post("/api/v1/evo/genes/extract", json={
            "task_ids": [task_id],
            "category": "capability",
            "min_support": 1,
            "min_confidence": 0.3,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["genes_extracted"] == 1
        assert data["source_tasks"] == 1
        mock_distiller.distill.assert_called_once()

    @patch("evo.api.genes_routes.RuleDistiller")
    def test_extract_genes_no_tasks(self, mock_distiller_class, client):
        """无任务记录时返回 0 条"""
        mock_distiller = MagicMock()
        mock_distiller_class.return_value = mock_distiller
        mock_distiller.distill.return_value = []

        response = client.post("/api/v1/evo/genes/extract", json={
            "min_support": 2,
            "min_confidence": 0.5,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["genes_extracted"] == 0
        assert "No task records" in data["message"]

    @patch("evo.api.genes_routes.RuleDistiller")
    def test_extract_genes_invalid_category(self, mock_distiller_class, client):
        """无效 category 返回 400"""
        response = client.post("/api/v1/evo/genes/extract", json={"category": "invalid"})
        assert response.status_code == 400
