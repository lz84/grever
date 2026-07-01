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
from sqlalchemy import func

from models import Capsule
from reins.common.database import get_db_session

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
    created_at: Optional[str] = None


class CapsuleListResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int


# ===========================================================================
# 辅助函数
# ===========================================================================

def _capsule_to_dict(capsule: Capsule) -> dict:
    """将 Capsule ORM 对象转为 dict，自动解析 JSON 列"""
    def _parse_json(value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return None
        return value

    return {
        "id": capsule.id,
        "schema_version": capsule.schema_version,
        "trigger": _parse_json(capsule.trigger),
        "gene_id": capsule.gene_id,
        "summary": capsule.summary,
        "confidence": capsule.confidence,
        "blast_radius": _parse_json(capsule.blast_radius),
        "outcome": _parse_json(capsule.outcome),
        "success_streak": capsule.success_streak,
        "content": capsule.content,
        "diff": capsule.diff,
        "strategy": _parse_json(capsule.strategy),
        "created_at": capsule.created_at,
    }


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

    db = get_db_session()
    try:
        # Filter by gene_id first
        query = db.query(Capsule)
        count_query = db.query(Capsule)

        if gene_id:
            query = query.filter(Capsule.gene_id == gene_id)
            count_query = count_query.filter(Capsule.gene_id == gene_id)

        total = count_query.count()

        offset = (page - 1) * page_size
        rows = query.order_by(Capsule.created_at.desc()).offset(offset).limit(page_size).all()

        # Filter by status (from JSON outcome column) in Python
        items = []
        for r in rows:
            if status:
                outcome = r.outcome
                if isinstance(outcome, str):
                    try:
                        outcome = json.loads(outcome)
                    except (json.JSONDecodeError, TypeError):
                        outcome = {}
                elif outcome is None:
                    outcome = {}
                if outcome.get("status") != status:
                    continue
            items.append(_capsule_to_dict(r))

        return CapsuleListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    finally:
        db.close()


# ===========================================================================
# GET /api/v1/evo/capsules/{capsule_id} — 查询单个 Capsule 详情
# ===========================================================================

@router.get("/{capsule_id}")
def get_capsule(capsule_id: str):
    """查询单个 Capsule 详情，不存在则返回 404"""
    db = get_db_session()
    try:
        row = db.query(Capsule).filter(Capsule.id == capsule_id).first()

        if row is None:
            raise HTTPException(status_code=404, detail=f"Capsule not found: {capsule_id}")

        return _capsule_to_dict(row)
    finally:
        db.close()


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

    db = get_db_session()
    try:
        # 先检查是否存在
        row = db.query(Capsule).with_entities(
            Capsule.id, Capsule.outcome
        ).filter(Capsule.id == capsule_id).first()

        if row is None:
            raise HTTPException(status_code=404, detail=f"Capsule not found: {capsule_id}")

        # 更新 outcome.status
        outcome = row[1] if row[1] else {}
        if isinstance(outcome, str):
            try:
                outcome = json.loads(outcome)
            except (json.JSONDecodeError, TypeError):
                outcome = {}

        outcome["status"] = new_status
        outcome["updated_at"] = datetime.now().isoformat()

        db.query(Capsule).filter(Capsule.id == capsule_id).update({
            "outcome": json.dumps(outcome, ensure_ascii=False),
        })
        db.commit()

        logger.info("Capsule %s promoted to %s", capsule_id, new_status)

        # 返回更新后的 Capsule
        updated = db.query(Capsule).filter(Capsule.id == capsule_id).first()
        return _capsule_to_dict(updated)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ===========================================================================
# PUT /api/v1/evo/capsules/{capsule_id}/deprecate — 标记为废弃
# ===========================================================================

@router.put("/{capsule_id}/deprecate")
def deprecate_capsule(capsule_id: str):
    """
    标记 Capsule 为废弃。
    更新 outcome.status 为 "deprecated"。
    """
    db = get_db_session()
    try:
        # 先检查是否存在
        row = db.query(Capsule).with_entities(
            Capsule.id, Capsule.outcome
        ).filter(Capsule.id == capsule_id).first()

        if row is None:
            raise HTTPException(status_code=404, detail=f"Capsule not found: {capsule_id}")

        # 更新 outcome.status
        outcome = row[1] if row[1] else {}
        if isinstance(outcome, str):
            try:
                outcome = json.loads(outcome)
            except (json.JSONDecodeError, TypeError):
                outcome = {}

        outcome["status"] = "deprecated"
        outcome["deprecated_at"] = datetime.now().isoformat()

        db.query(Capsule).filter(Capsule.id == capsule_id).update({
            "outcome": json.dumps(outcome, ensure_ascii=False),
        })
        db.commit()

        logger.info("Capsule %s deprecated", capsule_id)

        # 返回更新后的 Capsule
        updated = db.query(Capsule).filter(Capsule.id == capsule_id).first()
        return _capsule_to_dict(updated)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
