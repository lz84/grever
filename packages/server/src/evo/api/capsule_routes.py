"""
Sprint 105-3: Capsule 状态管理 API

提供 Capsule 的 promote / deprecate / 列表 / 详情端点。
直接操作 capsules DB 表。
"""

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from reins.common.database import get_db_manager
from persistence.tables import capsules as capsules_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/evo/capsules", tags=["evo-capsules"])

# ===========================================================================
# 请求/响应模型
# ===========================================================================

VALID_STATUSES = {"draft", "validated", "solidified", "deprecated"}


class PromoteRequest(BaseModel):
    status: str


class CapsuleRow(BaseModel):
    id: str
    schema_version: Optional[int] = None
    trigger: Optional[dict] = None
    gene_id: Optional[str] = None
    summary: Optional[str] = None
    confidence: Optional[float] = None
    blast_radius: Optional[dict] = None
    outcome: Optional[dict] = None
    success_streak: Optional[int] = None
    content: Optional[str] = None
    diff: Optional[str] = None
    strategy: Optional[dict] = None
    a2a: Optional[dict] = None
    created_at: Optional[str] = None


class CapsuleListResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int


# ===========================================================================
# 辅助函数
# ===========================================================================

def _row_to_dict(row) -> dict:
    """将 SQLAlchemy Row 转为 dict，自动解析 JSON 列和 DateTime"""
    d = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    # 解析 JSON 列
    for json_col in ("trigger", "blast_radius", "outcome", "strategy", "a2a"):
        val = d.get(json_col)
        if isinstance(val, str):
            try:
                d[json_col] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                d[json_col] = None
        elif val is None:
            d[json_col] = None
    # 格式化 DateTime
    for dt_col in ("created_at",):
        val = d.get(dt_col)
        if val is not None and not isinstance(val, str):
            d[dt_col] = str(val)
    return d


def _select_all_columns():
    """生成 SELECT 子句，列出所有列"""
    cols = [c.name for c in capsules_table.c]
    return ", ".join(cols)


# ===========================================================================
# GET /api/v1/evo/capsules — 查询 Capsule 列表
# ===========================================================================

@router.get("/")
def list_capsules(
    status: Optional[str] = Query(None, description="按状态过滤: draft/validated/solidified/deprecated"),
    gene_id: Optional[str] = Query(None, description="按基因 ID 过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """查询 Capsule 列表，支持 status 和 gene_id 过滤，分页"""
    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}. Must be one of {VALID_STATUSES}")

    where_clauses = []
    params = {}

    if status:
        # outcome 是 JSON 列，用 JSON 提取
        where_clauses.append("json_extract(outcome, '$.status') = :status")
        params["status"] = status

    if gene_id:
        where_clauses.append("gene_id = :gene_id")
        params["gene_id"] = gene_id

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    cols = _select_all_columns()

    db = get_db_manager()

    # 总数查询
    count_sql = f"SELECT COUNT(*) FROM capsules {where_sql}"
    with db.engine.connect() as conn:
        total = total = conn.execute(text(count_sql), params).scalar()

    # 分页查询
    offset = (page - 1) * page_size
    data_sql = f"SELECT {cols} FROM capsules {where_sql} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = page_size
    params["offset"] = offset

    with db.engine.connect() as conn:
        rows = rows = conn.execute(text(data_sql), params).fetchall()
    items = [_row_to_dict(r) for r in rows]

    return CapsuleListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ===========================================================================
# GET /api/v1/evo/capsules/{capsule_id} — 查询单个 Capsule 详情
# ===========================================================================

@router.get("/{capsule_id}")
def get_capsule(capsule_id: str):
    """查询单个 Capsule 详情，不存在则返回 404"""
    cols = _select_all_columns()
    db = get_db_manager()

    with db.engine.connect() as conn:
        row = row = conn.execute(
        text(f"SELECT {cols} FROM capsules WHERE id = :id"),
        {"id": capsule_id},
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Capsule not found: {capsule_id}")

    return _row_to_dict(row)


# ===========================================================================
# PUT /api/v1/evo/capsules/{capsule_id}/promote — 提升状态
# ===========================================================================

@router.put("/{capsule_id}/promote")
def promote_capsule(capsule_id: str, req: PromoteRequest):
    """
    提升 Capsule 状态。
    Body: {"status": "validated"} 或 {"status": "solidified"}
    """
    new_status = req.status
    if new_status not in ("validated", "solidified"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid promote status: {new_status}. Must be 'validated' or 'solidified'",
        )

    db = get_db_manager()

    # 先检查是否存在
    with db.engine.connect() as conn:
        row = row = conn.execute(
        text("SELECT id, outcome FROM capsules WHERE id = :id"),
        {"id": capsule_id},
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Capsule not found: {capsule_id}")

    # 更新 outcome.status
    outcome = row.outcome if row.outcome else {}
    if isinstance(outcome, str):
        try:
            outcome = json.loads(outcome)
        except (json.JSONDecodeError, TypeError):
            outcome = {}

    outcome["status"] = new_status
    outcome["updated_at"] = datetime.now().isoformat()

    with db.engine.connect() as conn:
        conn.execute(
        text("UPDATE capsules SET outcome = :outcome WHERE id = :id"),
        {"outcome": json.dumps(outcome, ensure_ascii=False), "id": capsule_id},
        )
        conn.commit()

    logger.info("Capsule %s promoted to %s", capsule_id, new_status)

    # 返回更新后的 Capsule
    cols = _select_all_columns()
    with db.engine.connect() as conn:
        updated = updated = conn.execute(
        text(f"SELECT {cols} FROM capsules WHERE id = :id"),
        {"id": capsule_id},
        ).fetchone()

    return _row_to_dict(updated)


# ===========================================================================
# PUT /api/v1/evo/capsules/{capsule_id}/deprecate — 标记为废弃
# ===========================================================================

@router.put("/{capsule_id}/deprecate")
def deprecate_capsule(capsule_id: str):
    """
    标记 Capsule 为废弃。
    更新 outcome.status 为 "deprecated"。
    """
    db = get_db_manager()

    # 先检查是否存在
    with db.engine.connect() as conn:
        row = row = conn.execute(
        text("SELECT id, outcome FROM capsules WHERE id = :id"),
        {"id": capsule_id},
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Capsule not found: {capsule_id}")

    # 更新 outcome.status
    outcome = row.outcome if row.outcome else {}
    if isinstance(outcome, str):
        try:
            outcome = json.loads(outcome)
        except (json.JSONDecodeError, TypeError):
            outcome = {}

    outcome["status"] = "deprecated"
    outcome["deprecated_at"] = datetime.now().isoformat()

    with db.engine.connect() as conn:
        conn.execute(
        text("UPDATE capsules SET outcome = :outcome WHERE id = :id"),
        {"outcome": json.dumps(outcome, ensure_ascii=False), "id": capsule_id},
        )
        conn.commit()

    logger.info("Capsule %s deprecated", capsule_id)

    # 返回更新后的 Capsule
    cols = _select_all_columns()
    with db.engine.connect() as conn:
        updated = updated = conn.execute(
        text(f"SELECT {cols} FROM capsules WHERE id = :id"),
        {"id": capsule_id},
        ).fetchone()

    return _row_to_dict(updated)
