"""Industry Capability Tags — Industry listing and agent tag endpoints."""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from reins.common.database import get_db
from models import Agent, Task, AgentTagWeight, IndustryCapabilityTag
from sqlalchemy import func, distinct, text
from .industry_tags_helpers import _row_to_response

router = APIRouter(prefix="/api/v1/industry-tags", tags=["industry-tags"])


@router.get("/")
async def list_all_tags(
    industry: Optional[str] = Query(None, description="按行业过滤"),
    status: Optional[str] = Query(None, description="按状态过滤（默认 active）"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """列出所有行业标签（支持分页和过滤）。"""
    cols = [
        IndustryCapabilityTag.id,
        IndustryCapabilityTag.industry,
        IndustryCapabilityTag.tag_name,
        IndustryCapabilityTag.tag_name_en,
        IndustryCapabilityTag.description,
        IndustryCapabilityTag.dimension,
        IndustryCapabilityTag.level,
        IndustryCapabilityTag.prerequisites,
        IndustryCapabilityTag.tools,
        IndustryCapabilityTag.examples,
        IndustryCapabilityTag.status,
        IndustryCapabilityTag.created_at,
        IndustryCapabilityTag.updated_at,
        IndustryCapabilityTag.replaced_by,
        IndustryCapabilityTag.version_major,
        IndustryCapabilityTag.version_minor,
        IndustryCapabilityTag.version_patch,
    ]
    query = db.query(*cols)
    if industry:
        query = query.filter(IndustryCapabilityTag.industry == industry)
    filter_status = status or 'active'
    query = query.filter(IndustryCapabilityTag.status == filter_status)
    total = db.query(IndustryCapabilityTag).filter(
        IndustryCapabilityTag.status == filter_status
    ).count()
    if industry:
        total = db.query(IndustryCapabilityTag).filter(
            IndustryCapabilityTag.industry == industry,
            IndustryCapabilityTag.status == filter_status,
        ).count()
    rows = query.order_by(
        IndustryCapabilityTag.industry.asc(),
        IndustryCapabilityTag.dimension.asc(),
        IndustryCapabilityTag.tag_name.asc(),
    ).offset(skip).limit(limit).all()
    items = [_row_to_response(r) for r in rows]
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/_industries")
async def list_industries(db: Session = Depends(get_db)):
    """List all industries that have tags."""
    rows = db.query(distinct(IndustryCapabilityTag.industry)).filter(
        IndustryCapabilityTag.status == 'active'
    ).order_by(IndustryCapabilityTag.industry).all()
    return [row[0] for row in rows]


@router.get("/_stats")
async def get_tag_stats(tag_id: Optional[str] = None, db: Session = Depends(get_db)):
    """统计标签在 tasks/agents 中的引用次数。"""
    result = {"tasks_using": [], "agents_using": [], "usage_count": 0}
    if tag_id:
        try:
            task_rows = db.query(Task).with_entities(Task.id, Task.title, Task.capability_tags).all()
            for row in task_rows:
                if row[2]:
                    tags = json.loads(row[2]) if isinstance(row[2], str) else row[2]
                    for dim_tags in (tags.values() if isinstance(tags, dict) else []):
                        if isinstance(dim_tags, list) and tag_id in dim_tags:
                            result["tasks_using"].append({"id": row[0], "title": row[1]})
                            break
            agent_rows = db.query(Agent).with_entities(Agent.id, Agent.name, Agent.capability_tags).all()
            for row in agent_rows:
                if row[2]:
                    tags = json.loads(row[2]) if isinstance(row[2], str) else row[2]
                    for dim_tags in (tags.values() if isinstance(tags, dict) else []):
                        if isinstance(dim_tags, list) and tag_id in dim_tags:
                            result["agents_using"].append({"id": row[0], "name": row[1]})
                            break
        except Exception:
            pass
        result["usage_count"] = len(result["tasks_using"]) + len(result["agents_using"])
    return result


@router.get("/_by-industry/{industry}")
async def list_tags_by_industry(industry: str, db: Session = Depends(get_db)):
    """List all tags for a specific industry."""
    rows = db.query(IndustryCapabilityTag).filter(
        IndustryCapabilityTag.industry == industry,
        IndustryCapabilityTag.status == 'active',
    ).order_by(IndustryCapabilityTag.dimension, IndustryCapabilityTag.tag_name).all()
    items = [_row_to_response(r) for r in rows]
    return {"items": items, "total": len(items), "industry": industry}


@router.get("/agent-tag-recommend")
async def get_agent_tag_recommend(agent_id: str, db: Session = Depends(get_db)):
    """推荐某 Agent 应该配置的行业标签，基于其历史执行任务聚合。"""
    class RecommendedTag(BaseModel):
        tag_id: str; count: int; tag_name: str = ""; dimension: str = ""
    class RecommendResponse(BaseModel):
        agent_id: str; recommended: dict; current: dict; missing: list

    agent_row = db.query(Agent).with_entities(Agent.capability_tags).filter(Agent.id == agent_id).first()
    current = {}
    if agent_row and agent_row[0]:
        try:
            current = json.loads(agent_row[0]) if isinstance(agent_row[0], str) else agent_row[0]
        except Exception:
            current = {}

    task_rows = db.query(Task).with_entities(Task.capability_tags).filter(
        Task.assigned_agent == agent_id,
        Task.status == 'done',
    ).all()
    dim_counts = {d: {} for d in ["business", "professional", "technical", "management"]}
    for row in task_rows:
        if not row[0]:
            continue
        try:
            caps = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        except Exception:
            continue
        if not isinstance(caps, dict):
            continue
        for dim in dim_counts:
            tags = caps.get(dim, [])
            if isinstance(tags, list):
                for t in tags:
                    if isinstance(t, str):
                        dim_counts[dim][t] = dim_counts[dim].get(t, 0) + 1

    all_tag_ids = [tid for counts in dim_counts.values() for tid in counts]
    tag_meta = {}
    if all_tag_ids:
        rows = db.query(IndustryCapabilityTag).with_entities(
            IndustryCapabilityTag.id, IndustryCapabilityTag.tag_name, IndustryCapabilityTag.dimension
        ).filter(IndustryCapabilityTag.id.in_(all_tag_ids)).all()
        tag_meta = {r[0]: {"tag_name": r[1], "dimension": r[2]} for r in rows}

    recommended = {d: [] for d in dim_counts}
    for dim, counts in dim_counts.items():
        for tid, cnt in sorted(counts.items(), key=lambda x: -x[1]):
            recommended[dim].append({"tag_id": tid, "count": cnt,
                "tag_name": tag_meta.get(tid, {}).get("tag_name", tid),
                "dimension": tag_meta.get(tid, {}).get("dimension", dim)})

    missing = []
    for dim, recs in recommended.items():
        current_tags = current.get(dim, []) if isinstance(current, dict) else []
        if not isinstance(current_tags, list):
            current_tags = []
        for rec in recs:
            if rec["tag_id"] not in current_tags:
                missing.append(rec["tag_id"])

    return RecommendResponse(agent_id=agent_id, recommended=recommended, current=current, missing=missing)


@router.get("/agent-tags")
async def get_agent_industry_tags(agent_id: str, db: Session = Depends(get_db)):
    """获取某 Agent 的行业标签（含元数据和来源标注）。"""
    class AgentTagItem(BaseModel):
        tag_id: str; tag_name: str; tag_name_en: str = ""; dimension: str; description: str = ""; source: str
    class AgentIndustryTagsResponse(BaseModel):
        agent_id: str; manual_tags: list[AgentTagItem]; inferred_tags: list[AgentTagItem]

    row = db.query(Agent).with_entities(Agent.capability_tags).filter(Agent.id == agent_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    caps_raw = row[0]
    if not caps_raw:
        return AgentIndustryTagsResponse(agent_id=agent_id, manual_tags=[], inferred_tags=[])
    try:
        caps = json.loads(caps_raw) if isinstance(caps_raw, str) else caps_raw
    except Exception:
        caps = {}

    industry_tag_ids = []
    for dim_tags in caps.values() if isinstance(caps, dict) else []:
        if isinstance(dim_tags, list):
            for t in dim_tags:
                if isinstance(t, str) and ":" in t:
                    industry_tag_ids.append(t)
    if not industry_tag_ids:
        return AgentIndustryTagsResponse(agent_id=agent_id, manual_tags=[], inferred_tags=[])

    rows = db.query(IndustryCapabilityTag).with_entities(
        IndustryCapabilityTag.id, IndustryCapabilityTag.tag_name,
        IndustryCapabilityTag.tag_name_en, IndustryCapabilityTag.description,
        IndustryCapabilityTag.dimension,
    ).filter(IndustryCapabilityTag.id.in_(industry_tag_ids)).all()
    tag_meta = {r[0]: {"tag_name": r[1], "tag_name_en": r[2] or "", "description": r[3] or "", "dimension": r[4]} for r in rows}

    inferred_rows = db.query(AgentTagWeight).with_entities(
        AgentTagWeight.tag
    ).filter(AgentTagWeight.agent_id == agent_id).all()
    inferred_tag_ids = set(r[0] for r in inferred_rows)
    manual, inferred = [], []
    for tid in industry_tag_ids:
        meta = tag_meta.get(tid, {"tag_name": tid, "tag_name_en": "", "description": "", "dimension": "professional"})
        item = AgentTagItem(tag_id=tid, tag_name=meta["tag_name"], tag_name_en=meta["tag_name_en"],
            dimension=meta["dimension"], description=meta["description"],
            source="inferred" if tid in inferred_tag_ids else "manual")
        if item.source == "inferred":
            inferred.append(item)
        else:
            manual.append(item)
    return AgentIndustryTagsResponse(agent_id=agent_id, manual_tags=manual, inferred_tags=inferred)
