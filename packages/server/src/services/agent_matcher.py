"""
Agent 自动匹配服务 Phase 2

支持多维度能力标签匹配、权重计算、负载感知
"""
import json
from loguru import logger
from typing import Dict, List, Set
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.agent import Agent, AgentTagWeight
from models.industry_tag import IndustryCapabilityTag
from reins.database import get_db_manager

DIMS = ["business", "professional", "technical", "management"]

def _resolve_tag_metadata(tag_ids: List[str]) -> Dict[str, dict]:
    """批量查询 industry_capability_tags 表，返回 {tag_id: metadata} 映射"""
    if not tag_ids:
        return {}
    engine = get_db_manager().engine
    with engine.connect() as conn:
        session = Session(bind=conn)
        try:
            rows = session.query(IndustryCapabilityTag).filter(
                IndustryCapabilityTag.id.in_(tag_ids)
            ).all()
            return {
                r.id: {
                    "tag_name": getattr(r, "tag_name", r.name),
                    "tag_name_en": getattr(r, "tag_name_en", None),
                    "dimension": getattr(r, "dimension", None),
                    "level": getattr(r, "level", None),
                    "description": r.description,
                }
                for r in rows
            }
        finally:
            session.close()

def _tags(capability_tags) -> Set[str]:
    """将多维能力标签展平为集合"""
    if isinstance(capability_tags, str):
        try:
            capability_tags = json.loads(capability_tags)
        except Exception:
            return set()
    if not capability_tags:
        return set()
    result: Set[str] = set()
    for dim in DIMS:
        v = capability_tags.get(dim, [])
        if isinstance(v, list):
            result.update(v)
    return result

def _get_agent_weights(agent_id: str) -> Dict[str, float]:
    engine = get_db_manager().engine
    with engine.connect() as conn:
        session = Session(bind=conn)
        try:
            rows = session.query(AgentTagWeight).filter(
                AgentTagWeight.agent_id == agent_id
            ).all()
            return {r.tag: r.weight for r in rows}
        finally:
            session.close()

def _get_online_agents() -> List[Dict]:
    engine = get_db_manager().engine
    with engine.connect() as conn:
        session = Session(bind=conn)
        try:
            rows = session.query(Agent).filter(Agent.status == "online").all()
            agents = []
            for r in rows:
                ct = {}
                if r.capability_tags:
                    try:
                        ct = json.loads(r.capability_tags) if isinstance(r.capability_tags, str) else r.capability_tags
                    except Exception:
                        ct = {}
                agents.append({
                    "id": r.id,
                    "name": r.name,
                    "current_tasks": r.current_tasks or 0,
                    "max_concurrent_tasks": r.max_concurrent_tasks or 1,
                    "capability_tags": ct,
                })
            return agents
        finally:
            session.close()

def match(capability_tags: Dict, min_score: float = 0.0, limit: int = 10) -> List[Dict]:
    """核心匹配函数：返回在线 Agent 的匹配排名"""
    required = _tags(capability_tags)
    if not required:
        return []

    # 预解析所有可能匹配的标签的元数据
    tag_metadata = _resolve_tag_metadata(sorted(required))

    results = []
    for agent in _get_online_agents():
        agent_tags = _tags(agent["capability_tags"])
        matched = required & agent_tags
        if not matched:
            continue

        w = _get_agent_weights(agent["id"])
        score = sum(w.get(t, 1.0) for t in matched) / len(required)
        if score < min_score:
            continue

        load_pct = agent["current_tasks"] / max(agent["max_concurrent_tasks"], 1) * 100
        matched_meta = {t: tag_metadata[t] for t in sorted(matched) if t in tag_metadata}
        results.append({
            "agent_id": agent["id"],
            "name": agent["name"],
            "score": round(score, 3),
            "matched_tags": sorted(matched),
            "matched_tags_metadata": matched_meta,
            "missing_tags": sorted(required - agent_tags),
            "load": round(load_pct, 1),
            "max_concurrent_tasks": agent["max_concurrent_tasks"],
        })

    results.sort(key=lambda x: (-x["score"], x["load"]))
    return results[:limit]

def match_for_project(tags: Dict) -> List[Dict]:
    return match(tags, min_score=0.3, limit=5)

def match_for_task(tags: Dict) -> List[Dict]:
    return match(tags, min_score=0.5, limit=3)

def match_for_goal(tags: Dict) -> List[Dict]:
    return match(tags, min_score=0.1, limit=3)

def update_weight(agent_id: str, tag: str, weight: float):
    engine = get_db_manager().engine
    with engine.begin() as conn:
        session = Session(bind=conn)
        try:
            existing = session.query(AgentTagWeight).filter(
                AgentTagWeight.agent_id == agent_id,
                AgentTagWeight.tag == tag
            ).first()
            from sqlalchemy import func as sa_func
            if existing:
                existing.weight = weight
                existing.last_observed = sa_func.CURRENT_TIMESTAMP
            else:
                new_weight = AgentTagWeight(
                    agent_id=agent_id,
                    tag=tag,
                    weight=weight,
                    last_observed=sa_func.CURRENT_TIMESTAMP,
                )
                session.add(new_weight)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
