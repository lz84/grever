"""
Vigil 角色管理 API

提供 RBAC 角色管理端点。
支持角色的创建、查询、更新和删除。
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from api.app_state import get_db_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/vigil/roles", tags=["vigil-roles"])

# ===========================================================================
# 请求/响应模型
# ===========================================================================


class RoleCreate(BaseModel):
    """创建角色请求"""
    name: str
    description: Optional[str] = None
    permissions: Optional[list[str]] = None
    level: Optional[int] = 1  # 角色等级，数字越大权限越高


class RoleUpdate(BaseModel):
    """更新角色请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[list[str]] = None
    level: Optional[int] = None
    status: Optional[str] = None  # active / inactive


class RoleListResponse(BaseModel):
    items: list[dict]
    total: int


class RoleAssignRequest(BaseModel):
    """分配角色请求"""
    agent_id: str


class RoleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    permissions: list[str]
    level: int
    status: str
    created_at: str
    updated_at: Optional[str]


# ===========================================================================
# 辅助函数
# ===========================================================================

ROLE_COLUMNS = [
    "id", "name", "description", "permissions", "level",
    "status", "created_at", "updated_at",
]

VALID_STATUSES = {"active", "inactive"}


def _row_to_dict(row) -> dict:
    """将 SQLAlchemy Row 转为 dict，自动解析 JSON 列和 DateTime"""
    d = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    # 解析 JSON 列
    val = d.get("permissions")
    if isinstance(val, str):
        try:
            d["permissions"] = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            d["permissions"] = []
    elif val is None:
        d["permissions"] = []
    # 格式化 DateTime
    for dt_col in ("created_at", "updated_at"):
        val = d.get(dt_col)
        if val is not None and not isinstance(val, str):
            d[dt_col] = str(val)
    return d


# ===========================================================================
# POST /api/v1/vigil/roles — 创建角色
# ===========================================================================

@router.post("/")
def create_role(req: RoleCreate):
    """
    创建一个新的 RBAC 角色。
    """
    db = get_db_manager()

    # 检查角色名是否已存在
    with db.engine.connect() as conn:
        existing = existing = conn.execute(
        text("SELECT id FROM roles WHERE name = :name"),
        {"name": req.name},
        ).fetchone()

    if existing:
        raise HTTPException(status_code=409, detail=f"Role already exists: {req.name}")

    role_id = f"role-{uuid.uuid4().hex[:12]}"
    now = datetime.now().isoformat()

    with db.engine.connect() as conn:
        conn.execute(
        text("""
        INSERT INTO roles (
        id, name, description, permissions, level, status,
        created_at, updated_at
        ) VALUES (
        :id, :name, :description, :permissions, :level, 'active',
        :created_at, :updated_at
        )
        """),
        {
        "id": role_id,
        "name": req.name,
        "description": req.description,
        "permissions": json.dumps(req.permissions, ensure_ascii=False) if req.permissions else "[]",
        "level": req.level if req.level is not None else 1,
        "created_at": now,
        "updated_at": now,
        },
        )
        conn.commit()

    logger.info("Role %s created (name=%s, level=%d)", role_id, req.name, req.level or 1)

    cols = ", ".join(ROLE_COLUMNS)
    with db.engine.connect() as conn:
        created = created = conn.execute(
        text(f"SELECT {cols} FROM roles WHERE id = :id"),
        {"id": role_id},
        ).fetchone()

    return _row_to_dict(created)


# ===========================================================================
# GET /api/v1/vigil/roles — 查询角色列表
# ===========================================================================

@router.get("/")
def list_roles(
    status: Optional[str] = Query(None, description="按状态过滤: active/inactive"),
    level: Optional[int] = Query(None, description="按等级过滤"),
    search: Optional[str] = Query(None, description="按名称搜索"),
):
    """查询角色列表，支持过滤和搜索"""
    if status and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {status}. Must be one of {VALID_STATUSES}",
        )

    where_clauses = []
    params: dict = {}

    if status:
        where_clauses.append("status = :status")
        params["status"] = status

    if level is not None:
        where_clauses.append("level = :level")
        params["level"] = level

    if search:
        where_clauses.append("name LIKE :search")
        params["search"] = f"%{search}%"

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    cols = ", ".join(ROLE_COLUMNS)
    db = get_db_manager()

    with db.engine.connect() as conn:
        rows = rows = conn.execute(
        text(f"SELECT {cols} FROM roles {where_sql} ORDER BY level DESC, name ASC"),
        params,
        ).fetchall()

    items = [_row_to_dict(r) for r in rows]

    return {
        "items": items,
        "total": len(items),
    }


# ===========================================================================
# GET /api/v1/vigil/roles/{role_id} — 查询角色详情
# ===========================================================================

@router.get("/{role_id}")
def get_role(role_id: str):
    """查询单个角色详情"""
    cols = ", ".join(ROLE_COLUMNS)
    db = get_db_manager()

    with db.engine.connect() as conn:
        row = row = conn.execute(
        text(f"SELECT {cols} FROM roles WHERE id = :id"),
        {"id": role_id},
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Role not found: {role_id}")

    return _row_to_dict(row)


# ===========================================================================
# PUT /api/v1/vigil/roles/{role_id} — 更新角色
# ===========================================================================

@router.put("/{role_id}")
def update_role(role_id: str, req: RoleUpdate):
    """
    更新角色信息。

    支持部分更新（只传需要修改的字段）。
    """
    db = get_db_manager()

    # 验证角色存在
    with db.engine.connect() as conn:
        existing = existing = conn.execute(
        text(f"SELECT {', '.join(ROLE_COLUMNS)} FROM roles WHERE id = :id"),
        {"id": role_id},
        ).fetchone()

    if existing is None:
        raise HTTPException(status_code=404, detail=f"Role not found: {role_id}")

    # 构建更新字段
    updates = {}
    now = datetime.now().isoformat()
    updates["updated_at"] = now

    if req.name is not None:
        # 检查新名称是否与其他角色冲突
        with db.engine.connect() as conn:
            name_conflict = name_conflict = conn.execute(
            text("SELECT id FROM roles WHERE name = :name AND id != :id"),
            {"name": req.name, "id": role_id},
            ).fetchone()
        if name_conflict:
            raise HTTPException(status_code=409, detail=f"Role name already exists: {req.name}")
        updates["name"] = req.name

    if req.description is not None:
        updates["description"] = req.description

    if req.permissions is not None:
        updates["permissions"] = json.dumps(req.permissions, ensure_ascii=False)

    if req.level is not None:
        updates["level"] = req.level

    if req.status is not None:
        if req.status not in VALID_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {req.status}. Must be one of {VALID_STATUSES}",
            )
        updates["status"] = req.status

    if len(updates) <= 1:  # 只有 updated_at
        return _row_to_dict(existing)

    # 构建 UPDATE 语句
    set_clauses = ", ".join(f"{k} = :{k}" for k in updates.keys())
    with db.engine.connect() as conn:
        conn.execute(
        text(f"UPDATE roles SET {set_clauses} WHERE id = :id"),
        {**updates, "id": role_id},
        )
        conn.commit()

    logger.info("Role %s updated (fields=%s)", role_id, list(updates.keys()))

    # 返回更新后的角色
    cols = ", ".join(ROLE_COLUMNS)
    with db.engine.connect() as conn:
        updated = updated = conn.execute(
        text(f"SELECT {cols} FROM roles WHERE id = :id"),
        {"id": role_id},
        ).fetchone()

    return _row_to_dict(updated)


# ===========================================================================
# DELETE /api/v1/vigil/roles/{role_id} — 删除角色
# ===========================================================================

@router.delete("/{role_id}")
def delete_role(role_id: str):
    """
    删除角色。

    软删除：将状态设为 inactive 并添加删除标记。
    """
    db = get_db_manager()

    # 验证角色存在
    with db.engine.connect() as conn:
        existing = existing = conn.execute(
        text("SELECT id, name, status FROM roles WHERE id = :id"),
        {"id": role_id},
        ).fetchone()

    if existing is None:
        raise HTTPException(status_code=404, detail=f"Role not found: {role_id}")

    if existing.status == "inactive":
        raise HTTPException(status_code=400, detail=f"Role {role_id} is already inactive/deleted")

    now = datetime.now().isoformat()

    # 软删除：更新状态
    with db.engine.connect() as conn:
        conn.execute(
        text("UPDATE roles SET status = 'inactive', updated_at = :updated_at WHERE id = :id"),
        {"updated_at": now, "id": role_id},
        )
        conn.commit()

    logger.info("Role %s deleted (soft delete)", role_id)

    return {
        "id": role_id,
        "name": existing.name,
        "status": "inactive",
        "deleted_at": now,
    }
