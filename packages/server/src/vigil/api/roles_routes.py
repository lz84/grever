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

from models import Role
from reins.common.database import get_db_session

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

VALID_STATUSES = {"active", "inactive"}


def _role_to_dict(role: Role) -> dict:
    """将 Role ORM 对象转为 dict，自动解析 JSON 列"""
    perms = role.permissions
    if isinstance(perms, str):
        try:
            perms = json.loads(perms)
        except (json.JSONDecodeError, TypeError):
            perms = []
    elif perms is None:
        perms = []

    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "permissions": perms,
        "level": role.level,
        "status": role.status,
        "created_at": role.created_at.isoformat() if isinstance(role.created_at, datetime) else str(role.created_at) if role.created_at else None,
        "updated_at": role.updated_at.isoformat() if isinstance(role.updated_at, datetime) else str(role.updated_at) if role.updated_at else None,
    }


# ===========================================================================
# POST /api/v1/vigil/roles — 创建角色
# ===========================================================================

@router.post("/")
def create_role(req: RoleCreate):
    """
    创建一个新的 RBAC 角色。
    """
    db = get_db_session()
    try:
        # 检查角色名是否已存在
        existing = db.query(Role).filter(Role.name == req.name).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Role already exists: {req.name}")

        now = datetime.now()
        role = Role(
            id=f"role-{uuid.uuid4().hex[:12]}",
            name=req.name,
            description=req.description,
            permissions=json.dumps(req.permissions, ensure_ascii=False) if req.permissions else "[]",
            level=req.level if req.level is not None else 1,
            status='active',
            created_at=now,
            updated_at=now,
        )
        db.add(role)
        db.commit()

        logger.info("Role %s created (name=%s, level=%d)", role.id, req.name, role.level)

        return _role_to_dict(role)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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

    db = get_db_session()
    try:
        query = db.query(Role)

        if status:
            query = query.filter(Role.status == status)

        if level is not None:
            query = query.filter(Role.level == level)

        if search:
            query = query.filter(Role.name.like(f"%{search}%"))

        rows = query.order_by(Role.level.desc(), Role.name.asc()).all()
        items = [_role_to_dict(r) for r in rows]

        return {
            "items": items,
            "total": len(items),
        }
    finally:
        db.close()


# ===========================================================================
# GET /api/v1/vigil/roles/{role_id} — 查询角色详情
# ===========================================================================

@router.get("/{role_id}")
def get_role(role_id: str):
    """查询单个角色详情"""
    db = get_db_session()
    try:
        row = db.query(Role).filter(Role.id == role_id).first()

        if row is None:
            raise HTTPException(status_code=404, detail=f"Role not found: {role_id}")

        return _role_to_dict(row)
    finally:
        db.close()


# ===========================================================================
# PUT /api/v1/vigil/roles/{role_id} — 更新角色
# ===========================================================================

@router.put("/{role_id}")
def update_role(role_id: str, req: RoleUpdate):
    """
    更新角色信息。

    支持部分更新（只传需要修改的字段）。
    """
    db = get_db_session()
    try:
        # 验证角色存在
        existing = db.query(Role).filter(Role.id == role_id).first()
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Role not found: {role_id}")

        # 构建更新字段
        now = datetime.now()
        updated = False

        if req.name is not None:
            # 检查新名称是否与其他角色冲突
            name_conflict = db.query(Role).filter(
                Role.name == req.name,
                Role.id != role_id,
            ).first()
            if name_conflict:
                raise HTTPException(status_code=409, detail=f"Role name already exists: {req.name}")
            existing.name = req.name
            updated = True

        if req.description is not None:
            existing.description = req.description
            updated = True

        if req.permissions is not None:
            existing.permissions = json.dumps(req.permissions, ensure_ascii=False)
            updated = True

        if req.level is not None:
            existing.level = req.level
            updated = True

        if req.status is not None:
            if req.status not in VALID_STATUSES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {req.status}. Must be one of {VALID_STATUSES}",
                )
            existing.status = req.status
            updated = True

        existing.updated_at = now
        db.commit()

        logger.info("Role %s updated", role_id)

        return _role_to_dict(existing)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ===========================================================================
# DELETE /api/v1/vigil/roles/{role_id} — 删除角色
# ===========================================================================

@router.delete("/{role_id}")
def delete_role(role_id: str):
    """
    删除角色。

    软删除：将状态设为 inactive 并添加删除标记。
    """
    db = get_db_session()
    try:
        # 验证角色存在
        existing = db.query(Role).with_entities(
            Role.id, Role.name, Role.status
        ).filter(Role.id == role_id).first()

        if existing is None:
            raise HTTPException(status_code=404, detail=f"Role not found: {role_id}")

        if existing[2] == "inactive":
            raise HTTPException(status_code=400, detail=f"Role {role_id} is already inactive/deleted")

        now = datetime.now()

        # 软删除：更新状态
        db.query(Role).filter(Role.id == role_id).update({
            "status": "inactive",
            "updated_at": now,
        })
        db.commit()

        logger.info("Role %s deleted (soft delete)", role_id)

        return {
            "id": role_id,
            "name": existing[1],
            "status": "inactive",
            "deleted_at": now.isoformat(),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
