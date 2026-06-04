"""
L4-API-V-002 Vigil Roles Routes API 测试

对照文档：docs/09-系统设计/25-测试用例总览.md → TC-API-V-002

覆盖用例：
- TC-API-V-002: RBAC 角色管理
  - POST /api/v1/vigil/roles — 创建角色
  - GET /api/v1/vigil/roles — 查询角色列表
  - GET /api/v1/vigil/roles/{role_id} — 查询角色详情
  - PUT /api/v1/vigil/roles/{role_id} — 更新角色
  - DELETE /api/v1/vigil/roles/{role_id} — 删除角色
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
        # roles 表
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS roles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                permissions TEXT DEFAULT '[]',
                level INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # agents 表（关联角色）
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'offline',
                capabilities TEXT,
                capability_tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.fixture
def client(test_db):
    """Create TestClient with in-memory SQLite and roles routes"""
    db_config = DatabaseConfig(provider="sqlite", path=":memory:")
    db_manager = DatabaseManager(db_config)
    db_manager._engine = test_db.get_bind()
    set_db_manager(db_manager)

    from vigil.api.roles_routes import router as roles_router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(roles_router)
    with TestClient(app) as tc:
        yield tc


# ===========================================================================
# TC-API-V-002-01: POST /api/v1/vigil/roles — 创建角色
# ===========================================================================

class TestCreateRole:
    """TC-API-V-002-01: 创建角色"""

    def test_create_role_success(self, client):
        """成功创建角色"""
        response = client.post("/api/v1/vigil/roles", json={
            "name": "admin",
            "description": "Administrator role",
            "permissions": ["read", "write", "delete"],
            "level": 10,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "admin"
        assert data["description"] == "Administrator role"
        assert data["permissions"] == ["read", "write", "delete"]
        assert data["level"] == 10
        assert data["status"] == "active"
        assert "id" in data
        assert data["id"].startswith("role-")
        assert "created_at" in data

    def test_create_role_minimal(self, client):
        """最小字段创建角色"""
        response = client.post("/api/v1/vigil/roles", json={
            "name": "viewer",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "viewer"
        assert data["description"] is None
        assert data["permissions"] == []
        assert data["level"] == 1
        assert data["status"] == "active"

    def test_create_role_with_default_level(self, client):
        """指定默认等级"""
        response = client.post("/api/v1/vigil/roles", json={
            "name": "guest",
            "level": 1,
        })
        assert response.status_code == 200
        assert response.json()["level"] == 1

    def test_create_role_duplicate_name(self, client):
        """角色名重复返回 409"""
        response = client.post("/api/v1/vigil/roles", json={
            "name": "unique-role",
        })
        assert response.status_code == 200

        response = client.post("/api/v1/vigil/roles", json={
            "name": "unique-role",
        })
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_role_persisted(self, client, test_db):
        """角色已持久化到数据库"""
        response = client.post("/api/v1/vigil/roles", json={
            "name": "persisted-role",
            "description": "Test role",
            "level": 5,
        })
        assert response.status_code == 200
        role_id = response.json()["id"]

        row = test_db.execute(
            text("SELECT name, description, level, status FROM roles WHERE id = :id"),
            {"id": role_id}
        ).fetchone()
        assert row is not None
        assert row[0] == "persisted-role"
        assert row[1] == "Test role"
        assert row[2] == 5
        assert row[3] == "active"


# ===========================================================================
# TC-API-V-002-02: GET /api/v1/vigil/roles — 查询角色列表
# ===========================================================================

class TestListRoles:
    """TC-API-V-002-02: 查询角色列表"""

    def test_list_roles_empty(self, client):
        """空数据库返回空列表"""
        response = client.get("/api/v1/vigil/roles")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_roles_with_data(self, client, test_db):
        """返回已创建的角色"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, description, permissions, level, status, created_at)
            VALUES (:id, :name, :desc, :perms, :level, :status, :created)
        """), {
            "id": "role-001",
            "name": "admin",
            "desc": "Admin",
            "perms": json.dumps(["*"]),
            "level": 10,
            "status": "active",
            "created": now,
        })
        test_db.execute(text("""
            INSERT INTO roles (id, name, description, level, status, created_at)
            VALUES (:id, :name, :desc, :level, :status, :created)
        """), {
            "id": "role-002",
            "name": "viewer",
            "desc": "Viewer",
            "level": 1,
            "status": "active",
            "created": now,
        })
        test_db.commit()

        response = client.get("/api/v1/vigil/roles")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_roles_filter_by_status(self, client, test_db):
        """按状态过滤"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "role-active", "name": "active-role", "status": "active", "created": now})
        test_db.execute(text("""
            INSERT INTO roles (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "role-inactive", "name": "inactive-role", "status": "inactive", "created": now})
        test_db.commit()

        response = client.get("/api/v1/vigil/roles?status=active")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "active"

        response = client.get("/api/v1/vigil/roles?status=inactive")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "inactive"

    def test_list_roles_invalid_status(self, client):
        """无效状态返回 400"""
        response = client.get("/api/v1/vigil/roles?status=invalid")
        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    def test_list_roles_filter_by_level(self, client, test_db):
        """按等级过滤"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, level, status, created_at)
            VALUES (:id, :name, :level, :status, :created)
        """), {"id": "role-high", "name": "high-role", "level": 10, "status": "active", "created": now})
        test_db.execute(text("""
            INSERT INTO roles (id, name, level, status, created_at)
            VALUES (:id, :name, :level, :status, :created)
        """), {"id": "role-low", "name": "low-role", "level": 1, "status": "active", "created": now})
        test_db.commit()

        response = client.get("/api/v1/vigil/roles?level=10")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["level"] == 10

    def test_list_roles_search_by_name(self, client, test_db):
        """按名称搜索"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "role-admin", "name": "admin", "status": "active", "created": now})
        test_db.execute(text("""
            INSERT INTO roles (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "role-user", "name": "user", "status": "active", "created": now})
        test_db.commit()

        response = client.get("/api/v1/vigil/roles?search=admin")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "admin"

    def test_list_roles_ordering(self, client, test_db):
        """验证角色按等级降序、名称升序排列"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, level, status, created_at)
            VALUES (:id, :name, :level, :status, :created)
        """), {"id": "role-a", "name": "aaa-role", "level": 1, "status": "active", "created": now})
        test_db.execute(text("""
            INSERT INTO roles (id, name, level, status, created_at)
            VALUES (:id, :name, :level, :status, :created)
        """), {"id": "role-b", "name": "bbb-role", "level": 5, "status": "active", "created": now})
        test_db.execute(text("""
            INSERT INTO roles (id, name, level, status, created_at)
            VALUES (:id, :name, :level, :status, :created)
        """), {"id": "role-c", "name": "ccc-role", "level": 10, "status": "active", "created": now})
        test_db.commit()

        response = client.get("/api/v1/vigil/roles")
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["name"] == "ccc-role"  # 最高等级
        assert data["items"][1]["name"] == "bbb-role"
        assert data["items"][2]["name"] == "aaa-role"  # 最低等级


# ===========================================================================
# TC-API-V-002-03: GET /api/v1/vigil/roles/{role_id} — 查询角色详情
# ===========================================================================

class TestGetRole:
    """TC-API-V-002-03: 查询角色详情"""

    def test_get_role_not_found(self, client):
        """角色不存在返回 404"""
        response = client.get("/api/v1/vigil/roles/nonexistent-role")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_role_success(self, client, test_db):
        """成功查询角色详情"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, description, permissions, level, status, created_at)
            VALUES (:id, :name, :desc, :perms, :level, :status, :created)
        """), {
            "id": "role-detail-test",
            "name": "detail-test-role",
            "desc": "Test role for detail",
            "perms": json.dumps(["read", "write"]),
            "level": 5,
            "status": "active",
            "created": now,
        })
        test_db.commit()

        response = client.get("/api/v1/vigil/roles/role-detail-test")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "role-detail-test"
        assert data["name"] == "detail-test-role"
        assert data["description"] == "Test role for detail"
        assert data["permissions"] == ["read", "write"]
        assert data["level"] == 5
        assert data["status"] == "active"
        assert "created_at" in data

    def test_get_role_inactive(self, client, test_db):
        """可以查询 inactive 状态的角色"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "role-inactive", "name": "inactive-role", "status": "inactive", "created": now})
        test_db.commit()

        response = client.get("/api/v1/vigil/roles/role-inactive")
        assert response.status_code == 200
        assert response.json()["status"] == "inactive"


# ===========================================================================
# TC-API-V-002-04: PUT /api/v1/vigil/roles/{role_id} — 更新角色
# ===========================================================================

class TestUpdateRole:
    """TC-API-V-002-04: 更新角色"""

    def test_update_role_not_found(self, client):
        """角色不存在返回 404"""
        response = client.put("/api/v1/vigil/roles/nonexistent-role", json={
            "name": "new-name",
        })
        assert response.status_code == 404

    def test_update_role_success(self, client, test_db):
        """成功更新角色"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, description, level, status, created_at)
            VALUES (:id, :name, :desc, :level, :status, :created)
        """), {
            "id": "role-update-test",
            "name": "original-name",
            "desc": "Original description",
            "level": 1,
            "status": "active",
            "created": now,
        })
        test_db.commit()

        response = client.put("/api/v1/vigil/roles/role-update-test", json={
            "name": "updated-name",
            "description": "Updated description",
            "level": 5,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "updated-name"
        assert data["description"] == "Updated description"
        assert data["level"] == 5
        assert "updated_at" in data

    def test_update_role_partial(self, client, test_db):
        """部分更新（只传 name）"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, description, level, status, created_at)
            VALUES (:id, :name, :desc, :level, :status, :created)
        """), {
            "id": "role-partial",
            "name": "original",
            "desc": "Original desc",
            "level": 1,
            "status": "active",
            "created": now,
        })
        test_db.commit()

        response = client.put("/api/v1/vigil/roles/role-partial", json={
            "description": "Only desc updated",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "original"  # 未更新
        assert data["description"] == "Only desc updated"

    def test_update_role_duplicate_name(self, client, test_db):
        """更新为已存在的角色名返回 409"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "role-a", "name": "role-a", "status": "active", "created": now})
        test_db.execute(text("""
            INSERT INTO roles (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "role-b", "name": "role-b", "status": "active", "created": now})
        test_db.commit()

        response = client.put("/api/v1/vigil/roles/role-a", json={
            "name": "role-b",
        })
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_update_role_status(self, client, test_db):
        """更新角色状态"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "role-status-test", "name": "status-test", "status": "active", "created": now})
        test_db.commit()

        response = client.put("/api/v1/vigil/roles/role-status-test", json={
            "status": "inactive",
        })
        assert response.status_code == 200
        assert response.json()["status"] == "inactive"

    def test_update_role_invalid_status(self, client, test_db):
        """无效状态返回 400"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "role-invalid", "name": "invalid-test", "status": "active", "created": now})
        test_db.commit()

        response = client.put("/api/v1/vigil/roles/role-invalid", json={
            "status": "deleted",  # 无效状态
        })
        assert response.status_code == 400

    def test_update_role_permissions(self, client, test_db):
        """更新权限列表"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, permissions, status, created_at)
            VALUES (:id, :name, :perms, :status, :created)
        """), {
            "id": "role-perms",
            "name": "perms-test",
            "perms": json.dumps(["read"]),
            "status": "active",
            "created": now,
        })
        test_db.commit()

        response = client.put("/api/v1/vigil/roles/role-perms", json={
            "permissions": ["read", "write", "execute"],
        })
        assert response.status_code == 200
        assert response.json()["permissions"] == ["read", "write", "execute"]


# ===========================================================================
# TC-API-V-002-05: DELETE /api/v1/vigil/roles/{role_id} — 删除角色
# ===========================================================================

class TestDeleteRole:
    """TC-API-V-002-05: 删除角色（软删除）"""

    def test_delete_role_not_found(self, client):
        """角色不存在返回 404"""
        response = client.delete("/api/v1/vigil/roles/nonexistent-role")
        assert response.status_code == 404

    def test_delete_role_success(self, client, test_db):
        """成功软删除角色"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "role-delete-test", "name": "delete-test", "status": "active", "created": now})
        test_db.commit()

        response = client.delete("/api/v1/vigil/roles/role-delete-test")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "role-delete-test"
        assert data["status"] == "inactive"
        assert "deleted_at" in data

        # 验证数据库中已更新
        row = test_db.execute(
            text("SELECT status FROM roles WHERE id = :id"),
            {"id": "role-delete-test"}
        ).fetchone()
        assert row[0] == "inactive"

    def test_delete_role_already_inactive(self, client, test_db):
        """重复删除返回 400"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "role-already-deleted", "name": "already-deleted", "status": "inactive", "created": now})
        test_db.commit()

        response = client.delete("/api/v1/vigil/roles/role-already-deleted")
        assert response.status_code == 400
        assert "already inactive" in response.json()["detail"]

    def test_delete_role_returns_name(self, client, test_db):
        """删除响应包含角色名"""
        now = datetime.now().isoformat()
        test_db.execute(text("""
            INSERT INTO roles (id, name, status, created_at)
            VALUES (:id, :name, :status, :created)
        """), {"id": "role-named", "name": "Named Role", "status": "active", "created": now})
        test_db.commit()

        response = client.delete("/api/v1/vigil/roles/role-named")
        assert response.status_code == 200
        assert response.json()["name"] == "Named Role"