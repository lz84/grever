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
from sqlalchemy.orm import Session

from models import EvolutionEvent, Capsule
from reins.common.database import get_db_session

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


def _event_to_dict(event: EvolutionEvent) -> dict:
    """将 EvolutionEvent ORM 对象转为 dict，自动解析 JSON 列"""
    def _parse_json(value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return None
        return value

    return {
        "id": event.id,
        "schema_version": event.schema_version,
        "parent_id": event.parent_id,
        "intent": event.intent,
        "signals": _parse_json(event.signals),
        "genes_used": _parse_json(event.genes_used),
        "mutation_id": event.mutation_id,
        "blast_radius": _parse_json(event.blast_radius),
        "outcome": _parse_json(event.outcome),
        "capsule_id": event.capsule_id,
        "env_fingerprint": _parse_json(event.env_fingerprint),
        "meta": _parse_json(event.meta),
        "created_at": event.created_at,
    }


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
    """查询进化事件列表，支持过滤和分页
    
    注: evolution_events 表结构为简化版，返回空列表。
    完整 schema 待后续迁移后启用。
    """
    return EvolutionEventListResponse(
        items=[],
        total=0,
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
    now = str(datetime.now())

    # 如果有 parent_id，验证其存在
    if req.parent_id:
        db = get_db_session()
        try:
            parent_row = db.query(EvolutionEvent).filter(EvolutionEvent.id == req.parent_id).first()
            if parent_row is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Parent event not found: {req.parent_id}",
                )
        finally:
            db.close()

    db = get_db_session()
    try:
        event = EvolutionEvent(
            id=event_id,
            schema_version=req.schema_version or "1.0",
            parent_id=req.parent_id,
            intent=req.intent,
            signals=json.dumps(req.signals, ensure_ascii=False) if req.signals else None,
            genes_used=json.dumps(req.genes_used, ensure_ascii=False) if req.genes_used else None,
            mutation_id=req.mutation_id,
            blast_radius=json.dumps(req.blast_radius, ensure_ascii=False) if req.blast_radius else None,
            outcome=json.dumps(req.outcome, ensure_ascii=False) if req.outcome else None,
            capsule_id=req.capsule_id,
            env_fingerprint=json.dumps(req.env_fingerprint, ensure_ascii=False) if req.env_fingerprint else None,
            meta=json.dumps(req.meta, ensure_ascii=False) if req.meta else None,
            created_at=now,
        )
        db.add(event)
        db.commit()

        logger.info("Evolution event %s created (intent=%s)", event_id, req.intent)

        return _event_to_dict(event)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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
    db = get_db_session()
    try:
        # 查找事件
        row = db.query(EvolutionEvent).with_entities(
            EvolutionEvent.id, EvolutionEvent.meta, EvolutionEvent.capsule_id
        ).filter(EvolutionEvent.id == event_id).first()

        if row is None:
            raise HTTPException(status_code=404, detail=f"Evolution event not found: {event_id}")

        # 检查是否已经回滚
        existing_meta = row[1]
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
        now = str(datetime.now())
        existing_meta["reverted"] = True
        existing_meta["reverted_at"] = now
        if req and req.reason:
            existing_meta["revert_reason"] = req.reason

        db.query(EvolutionEvent).filter(EvolutionEvent.id == event_id).update({
            "meta": json.dumps(existing_meta, ensure_ascii=False),
        })
        db.commit()

        # 如果关联了 Capsule，标记为 deprecated
        capsule_id = row[2]
        if capsule_id:
            cap_row = db.query(Capsule).with_entities(
                Capsule.id, Capsule.outcome
            ).filter(Capsule.id == capsule_id).first()

            if cap_row:
                cap_outcome = cap_row[1]
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

                db.query(Capsule).filter(Capsule.id == capsule_id).update({
                    "outcome": json.dumps(cap_outcome, ensure_ascii=False),
                })
                db.commit()
                logger.info("Capsule %s deprecated due to event revert", capsule_id)

        logger.info("Evolution event %s reverted (reason=%s)", event_id, req.reason if req else None)

        return {
            "event_id": event_id,
            "reverted": True,
            "reverted_at": now,
            "capsule_deprecated": capsule_id is not None,
            "reason": req.reason if req else None,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
