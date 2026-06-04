"""Industry Capability Tags — Industry listing and agent tag endpoints."""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from reins.common.database import get_db
from .industry_tags_helpers import _row_to_response

router = APIRouter(prefix="/api/v1/industry-tags", tags=["industry-tags"])


@router.get("/_industries")
async def list_industries(db: Session = Depends(get_db)):
    """List all industries that have tags."""
    rows = db.execute(
        text("SELECT DISTINCT industry FROM industry_capability_tags WHERE status = 'active' ORDER BY industry")
    ).fetchall()
    return [row[0] for row in rows]


@router.get("/_stats")
async def get_tag_stats(tag_id: Optional[str] = None, db: Session = Depends(get_db)):
    """统计标签在 tasks/agents 中的引用次数。"""
    from .industry_tags_helpers import _count_tag_references
    result = {"tasks_using": [], "agents_using": [], "usage_count": 0}
    if tag_id:
        try:
            cur = db.execute(text("SELECT id, title, capability_tags FROM tasks"))
            for row in cur.fetchall():
                if row[2]:
                    tags = json.loads(row[2]) if isinstance(row[2], str) else row[2]
                    for dim_tags in (tags.values() if isinstance(tags, dict) else []):
                        if isinstance(dim_tags, list) and tag_id in dim_tags:
                            result["tasks_using"].append({"id": row[0], "title": row[1]})
                            break
            cur = db.execute(text("SELECT id, name, capability_tags FROM agents"))
            for row in cur.fetchall():
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
    rows = db.execute(
        text("SELECT * FROM industry_capability_tags WHERE industry = :industry AND status = 'active' ORDER BY dimension, tag_name"),
        {"industry": industry}
    ).fetchall()
    items = [_row_to_response(row) for row in rows]
    return {"items": items, "total": len(items), "industry": industry}


@router.get("/agent-tag-recommend")
async def get_agent_tag_recommend(agent_id: str, db: Session = Depends(get_db)):
    """推荐某 Agent 应该配置的行业标签，基于其历史执行任务聚合。"""
    from pydantic import BaseModel
    class RecommendedTag(BaseModel):
        tag_id: str; count: int; tag_name: str = ""; dimension: str = ""
    class RecommendResponse(BaseModel):
        agent_id: str; recommended: dict; current: dict; missing: list

    agent_row = db.execute(text("SELECT capability_tags FROM agents WHERE id = :aid"), {"aid": agent_id}).fetchone()
    current = {}
    if agent_row and agent_row[0]:
        try: current = json.loads(agent_row[0]) if isinstance(agent_row[0], str) else agent_row[0]
        except Exception: current = {}

    task_rows = db.execute(text("SELECT capability_tags FROM tasks WHERE assigned_agent = :aid AND status = 'done'"), {"aid": agent_id}).fetchall()
    dim_counts = {d: {} for d in ["business", "professional", "technical", "management"]}
    for row in task_rows:
        if not row[0]: continue
        try: caps = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        except Exception: continue
        if not isinstance(caps, dict): continue
        for dim in dim_counts:
            tags = caps.get(dim, [])
            if isinstance(tags, list):
                for t in tags:
                    if isinstance(t, str): dim_counts[dim][t] = dim_counts[dim].get(t, 0) + 1

    all_tag_ids = [tid for counts in dim_counts.values() for tid in counts]
    tag_meta = {}
    if all_tag_ids:
        placeholders = ", ".join([f":t{i}" for i in range(len(all_tag_ids))])
        params = {f"t{i}": tid for i, tid in enumerate(all_tag_ids)}
        rows = db.execute(text(f"SELECT id, tag_name, dimension FROM industry_capability_tags WHERE id IN ({placeholders})"), params).fetchall()
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
        if not isinstance(current_tags, list): current_tags = []
        for rec in recs:
            if rec["tag_id"] not in current_tags: missing.append(rec["tag_id"])

    return RecommendResponse(agent_id=agent_id, recommended=recommended, current=current, missing=missing)


@router.get("/agent-tags")
async def get_agent_industry_tags(agent_id: str, db: Session = Depends(get_db)):
    """获取某 Agent 的行业标签（含元数据和来源标注）。"""
    from pydantic import BaseModel
    class AgentTagItem(BaseModel):
        tag_id: str; tag_name: str; tag_name_en: str = ""; dimension: str; description: str = ""; source: str
    class AgentIndustryTagsResponse(BaseModel):
        agent_id: str; manual_tags: list[AgentTagItem]; inferred_tags: list[AgentTagItem]

    row = db.execute(text("SELECT capability_tags FROM agents WHERE id = :aid"), {"aid": agent_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    caps_raw = row[0]
    if not caps_raw:
        return AgentIndustryTagsResponse(agent_id=agent_id, manual_tags=[], inferred_tags=[])
    try: caps = json.loads(caps_raw) if isinstance(caps_raw, str) else caps_raw
    except Exception: caps = {}

    industry_tag_ids = []
    for dim_tags in caps.values() if isinstance(caps, dict) else []:
        if isinstance(dim_tags, list):
            for t in dim_tags:
                if isinstance(t, str) and ":" in t: industry_tag_ids.append(t)
    if not industry_tag_ids:
        return AgentIndustryTagsResponse(agent_id=agent_id, manual_tags=[], inferred_tags=[])

    placeholders = ", ".join([f":t{i}" for i in range(len(industry_tag_ids))])
    params = {f"t{i}": tid for i, tid in enumerate(industry_tag_ids)}
    rows = db.execute(text(f"SELECT id, tag_name, tag_name_en, description, dimension FROM industry_capability_tags WHERE id IN ({placeholders})"), params).fetchall()
    tag_meta = {r[0]: {"tag_name": r[1], "tag_name_en": r[2] or "", "description": r[3] or "", "dimension": r[4]} for r in rows}

    inferred_rows = db.execute(text("SELECT tag FROM agent_tag_weights WHERE agent_id = :aid"), {"aid": agent_id}).fetchall()
    inferred_tag_ids = set(r[0] for r in inferred_rows)
    manual, inferred = [], []
    for tid in industry_tag_ids:
        meta = tag_meta.get(tid, {"tag_name": tid, "tag_name_en": "", "description": "", "dimension": "professional"})
        item = AgentTagItem(tag_id=tid, tag_name=meta["tag_name"], tag_name_en=meta["tag_name_en"],
            dimension=meta["dimension"], description=meta["description"],
            source="inferred" if tid in inferred_tag_ids else "manual")
        if item.source == "inferred": inferred.append(item)
        else: manual.append(item)
    return AgentIndustryTagsResponse(agent_id=agent_id, manual_tags=manual, inferred_tags=inferred)
