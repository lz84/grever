"""
Evo 进化域 - Evolution Events API

提供进化事件记录和回滚端点。
直接操作 evolution_events DB 表。
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

router = APIRouter(prefix="/api/v1/evo/evolution-events", tags=["evo-evolution-events"])

# ===========================================================================
# 请求/响应模型
# ===========================================================================


class EvolutionEventCreate(BaseModel):
    """创建进化事件请求"""
    parent_id: Optional[str] = None
    intent: str
    signals: Optional[list[str]] = None
    genes_used: Optional[list[str]] = None
    mutation_id: Optional[str] = None
    blast_radius: Optional[dict] = None
    outcome: Optional[dict] = None
    capsule_id: Optional[str] = None
    env_fingerprint: Optional[dict] = None
    meta: Optional[dict] = None
    schema_version: Optional[str] = "1.0"


class EvolutionEventRevertRequest(BaseModel):
    """回滚请求"""
    reason: Optional[str] = None


class EvolutionEventListResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int


# ===========================================================================
# 辅助函数
# ===========================================================================

EVENT_COLUMNS = [
    "id", "schema_version", "parent_id", "intent", "signals",
    "genes_used", "mutation_id", "blast_radius", "outcome",
    "capsule_id", "env_fingerprint", "meta", "created_at",
]


def _row_to_dict(row) -> dict:
    """将 SQLAlchemy Row 转为 dict，自动解析 JSON 列和 DateTime"""
    d = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    for json_col in ("signals", "genes_used", "blast_radius", "outcome",
                     "env_fingerprint", "meta"):
        val = d.get(json_col)
        if isinstance(val, str):
            try:
                d[json_col] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                d[json_col] = None
        elif val is None:
            d[json_col] = None
    for dt_col in ("created_at",):
        val = d.get(dt_col)
        if val is not None and not isinstance(val, str):
            d[dt_col] = str(val)
    return d


# ===========================================================================
# GET /api/v1/evo/evolution-events — 查询进化事件列表
# ===========================================================================

@router.get("/")
def list_evolution_events(
    intent: Optional[str] = Query(None, description="按意图过滤"),
    capsule_id: Optional[str] = Query(None, description="按 Capsule ID 过滤"),
    mutation_id: Optional[str] = Query(None, description="按变异 ID 过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """查询进化事件列表，支持过滤和分页"""
    where_clauses = []
    params: dict = {}

    if intent:
        where_clauses.append("intent = :intent")
        params["intent"] = intent

    if capsule_id:
        where_clauses.append("capsule_id = :capsule_id")
        params["capsule_id"] = capsule_id

    if mutation_id:
        where_clauses.append("mutation_id = :mutation_id")
        params["mutation_id"] = mutation_id

    # 排除已回滚的事件（除非明确要求）
    where_clauses.append("COALESCE(json_extract(meta, '$.reverted'), 0) = 0")

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    cols = ", ".join(EVENT_COLUMNS)
    db = get_db_manager()

    # 总数查询
    count_sql = f"SELECT COUNT(*) FROM evolution_events {where_sql}"
    with db.engine.connect() as conn:
        total = total = conn.execute(text(count_sql), params).scalar()

    # 分页查询
    offset = (page - 1) * page_size
    data_sql = (
        f"SELECT {cols} FROM evolution_events {where_sql} "
        "ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    )
    params["limit"] = page_size
    params["offset"] = offset

    with db.engine.connect() as conn:
        rows = rows = conn.execute(text(data_sql), params).fetchall()
    items = [_row_to_dict(r) for r in rows]

    return EvolutionEventListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ===========================================================================
# POST /api/v1/evo/evolution-events — 创建进化事件
# ===========================================================================

@router.post("/")
def create_evolution_event(req: EvolutionEventCreate):
    """
    记录一次进化事件。
    """
    event_id = f"evt-{uuid.uuid4().hex[:12]}"
    now = datetime.now().isoformat()

    # 如果有 parent_id，验证其存在
    if req.parent_id:
        db = get_db_manager()
        with db.engine.connect() as conn:
            parent_row = parent_row = conn.execute(
            text("SELECT id FROM evolution_events WHERE id = :id"),
            {"id": req.parent_id},
            ).fetchone()
        if parent_row is None:
            raise HTTPException(
                status_code=400,
                detail=f"Parent event not found: {req.parent_id}",
            )

    db = get_db_manager()
    with db.engine.connect() as conn:
        conn.execute(
        text("""
        INSERT INTO evolution_events (
        id, schema_version, parent_id, intent, signals,
        genes_used, mutation_id, blast_radius, outcome,
        capsule_id, env_fingerprint, meta, created_at
        ) VALUES (
        :id, :schema_version, :parent_id, :intent, :signals,
        :genes_used, :mutation_id, :blast_radius, :outcome,
        :capsule_id, :env_fingerprint, :meta, :created_at
        )
        """),
        {
        "id": event_id,
        "schema_version": req.schema_version or "1.0",
        "parent_id": req.parent_id,
        "intent": req.intent,
        "signals": json.dumps(req.signals, ensure_ascii=False) if req.signals else None,
        "genes_used": json.dumps(req.genes_used, ensure_ascii=False) if req.genes_used else None,
        "mutation_id": req.mutation_id,
        "blast_radius": json.dumps(req.blast_radius, ensure_ascii=False) if req.blast_radius else None,
        "outcome": json.dumps(req.outcome, ensure_ascii=False) if req.outcome else None,
        "capsule_id": req.capsule_id,
        "env_fingerprint": json.dumps(req.env_fingerprint, ensure_ascii=False) if req.env_fingerprint else None,
        "meta": json.dumps(req.meta, ensure_ascii=False) if req.meta else None,
        "created_at": now,
        },
        )
        conn.commit()

    logger.info("Evolution event %s created (intent=%s)", event_id, req.intent)

    # 返回创建后的事件
    cols = ", ".join(EVENT_COLUMNS)
    with db.engine.connect() as conn:
        created = created = conn.execute(
        text(f"SELECT {cols} FROM evolution_events WHERE id = :id"),
        {"id": event_id},
        ).fetchone()

    return _row_to_dict(created)


# ===========================================================================
# POST /api/v1/evo/evolution-events/{event_id}/revert — 回滚进化事件
# ===========================================================================

@router.post("/{event_id}/revert")
def revert_evolution_event(event_id: str, req: Optional[EvolutionEventRevertRequest] = None):
    """
    回滚指定的进化事件。

    - 标记事件为 reverted
    - 如果事件关联了 Capsule，也标记 Capsule 为 deprecated
    - 可选提供回滚原因
    """
    db = get_db_manager()

    # 查找事件
    with db.engine.connect() as conn:
        row = row = conn.execute(
        text("SELECT id, meta, capsule_id FROM evolution_events WHERE id = :id"),
        {"id": event_id},
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Evolution event not found: {event_id}")

    # 检查是否已经回滚
    existing_meta = row.meta
    if isinstance(existing_meta, str):
        try:
            existing_meta = json.loads(existing_meta)
        except (json.JSONDecodeError, TypeError):
            existing_meta = {}
    elif existing_meta is None:
        existing_meta = {}

    if existing_meta.get("reverted"):
        raise HTTPException(status_code=400, detail=f"Event {event_id} already reverted")

    # 更新 meta
    now = datetime.now().isoformat()
    existing_meta["reverted"] = True
    existing_meta["reverted_at"] = now
    if req and req.reason:
        existing_meta["revert_reason"] = req.reason

    with db.engine.connect() as conn:
        conn.execute(
        text("UPDATE evolution_events SET meta = :meta WHERE id = :id"),
        {"meta": json.dumps(existing_meta, ensure_ascii=False), "id": event_id},
        )
        conn.commit()

    # 如果关联了 Capsule，标记为 deprecated
    capsule_id = row.capsule_id
    if capsule_id:
        with db.engine.connect() as conn:
            cap_row = cap_row = conn.execute(
            text("SELECT id, outcome FROM capsules WHERE id = :id"),
            {"id": capsule_id},
            ).fetchone()

        if cap_row:
            cap_outcome = cap_row.outcome
            if isinstance(cap_outcome, str):
                try:
                    cap_outcome = json.loads(cap_outcome)
                except (json.JSONDecodeError, TypeError):
                    cap_outcome = {}
            elif cap_outcome is None:
                cap_outcome = {}

            cap_outcome["status"] = "deprecated"
            cap_outcome["deprecated_at"] = now
            cap_outcome["deprecated_by_event_revert"] = event_id

            with db.engine.connect() as conn:
                conn.execute(
                text("UPDATE capsules SET outcome = :outcome WHERE id = :id"),
                {"outcome": json.dumps(cap_outcome, ensure_ascii=False), "id": capsule_id},
                )
                conn.commit()
            logger.info("Capsule %s deprecated due to event revert", capsule_id)

    logger.info("Evolution event %s reverted (reason=%s)", event_id, req.reason if req else None)

    return {
        "event_id": event_id,
        "reverted": True,
        "reverted_at": now,
        "capsule_deprecated": capsule_id is not None,
        "reason": req.reason if req else None,
    }
