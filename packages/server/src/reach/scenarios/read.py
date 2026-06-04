"""
Scenario 读端点 — list, get, status, fullset

职责：
1. GET / — 列表（支持多条件过滤）
2. GET /{scenario_id} — 详情
3. GET /{scenario_id}/status — 状态
4. GET/PUT /{scenario_id}/fullset — fullset 数据
"""

import json
from typing import List, Optional, Any

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from reins.common.database import get_db
from models.scenario import Scenario, ScenarioSummary

# Import helpers from crud
from .crud import _count_projects, _build_scenario_response

router = APIRouter(tags=["scenarios"])


@router.get("/", response_model=List[ScenarioSummary])
def list_scenarios(
    category: Optional[str] = Query(None, description="按分类过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    source: Optional[str] = Query(None, description="按来源过滤"),
    q: Optional[str] = Query(None, description="搜索关键词"),
    sort: Optional[str] = Query("success_rate", description="排序字段"),
    order: Optional[str] = Query("desc", description="asc 或 desc"),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    try:
        query = db.query(Scenario)
        if category:
            query = query.filter(Scenario.category == category)
        if status:
            query = query.filter(Scenario.status == status)
        if source:
            query = query.filter(Scenario.source == source)
        if q:
            query = query.filter(
                (Scenario.name.like(f"%{q}%"))
                | (Scenario.description.like(f"%{q}%"))
                | (Scenario.scenario_desc.like(f"%{q}%"))
            )
        if sort == "success_rate":
            query = query.order_by(Scenario.success_rate.desc() if order == "desc" else Scenario.success_rate.asc())
        elif sort == "usage_count":
            query = query.order_by(Scenario.usage_count.desc() if order == "desc" else Scenario.usage_count.asc())
        elif sort == "avg_duration_ms":
            query = query.order_by(Scenario.avg_duration_ms.desc() if order == "desc" else Scenario.avg_duration_ms.asc())
        elif sort == "updated_at":
            query = query.order_by(Scenario.updated_at.desc() if order == "desc" else Scenario.updated_at.asc())
        scenarios = query.offset(skip).limit(limit).all()
        return [
            ScenarioSummary(
                id=s.id, name=s.name, category=s.category, status=s.status,
                version=s.version, level=getattr(s, 'level', None),
                trust_level=getattr(s, 'trust_level', None),
                source=getattr(s, 'source', None),
                success_rate=s.success_rate or 0.0,
                avg_duration_ms=s.avg_duration_ms or 0.0,
                usage_count=s.usage_count,
                scenario_desc=s.scenario_desc[:100] if s.scenario_desc else "",
                project_count=_count_projects(db, s.id),
                created_at=s.created_at.isoformat() if hasattr(s.created_at, 'isoformat') and s.created_at else str(s.created_at) if s.created_at else None,
                updated_at=s.updated_at.isoformat() if hasattr(s.updated_at, 'isoformat') and s.updated_at else str(s.updated_at) if s.updated_at else None,
            )
            for s in scenarios
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询场景列表失败: {str(e)}")


@router.get("/{scenario_id}/status")
def get_scenario_status(scenario_id: str, db: Session = Depends(get_db)):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {"scenario_id": scenario_id, "status": scenario.status}


@router.get("/{scenario_id}")
def get_scenario(scenario_id: str, db: Session = Depends(get_db)):
    try:
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        return _build_scenario_response(db, scenario)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询场景详情失败: {str(e)}")


# === Fullset ===

class FullsetResponse(BaseModel):
    scenario_id: str
    goal_tags: Optional[dict] = None
    projects: Optional[list] = None


class FullsetUpdateRequest(BaseModel):
    goal_tags: Optional[dict] = None
    projects: Optional[list] = None


@router.get("/{scenario_id}/fullset", response_model=FullsetResponse)
def get_scenario_fullset(scenario_id: str, db: Session = Depends(get_db)):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    fullset_data = scenario.fullset
    if isinstance(fullset_data, str):
        try:
            fullset_data = json.loads(fullset_data)
        except Exception:
            fullset_data = None
    return FullsetResponse(
        scenario_id=scenario_id,
        goal_tags=fullset_data.get("goal_tags") if fullset_data else None,
        projects=fullset_data.get("projects") if fullset_data else None,
    )


@router.put("/{scenario_id}/fullset", response_model=FullsetResponse)
def update_scenario_fullset(scenario_id: str, data: FullsetUpdateRequest, db: Session = Depends(get_db)):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    fullset_data = scenario.fullset
    if isinstance(fullset_data, str):
        try:
            fullset_data = json.loads(fullset_data)
        except Exception:
            fullset_data = {}
    if fullset_data is None:
        fullset_data = {}
    if data.goal_tags is not None:
        fullset_data["goal_tags"] = data.goal_tags
    if data.projects is not None:
        fullset_data["projects"] = data.projects
    scenario.fullset = json.dumps(fullset_data)
    db.commit()
    db.refresh(scenario)
    return FullsetResponse(
        scenario_id=scenario_id,
        goal_tags=fullset_data.get("goal_tags"),
        projects=fullset_data.get("projects"),
    )
