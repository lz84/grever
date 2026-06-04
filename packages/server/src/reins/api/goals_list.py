"""Goals API: list & active endpoints."""
from loguru import logger

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sqla_func

from models.goal import Goal, GoalResponse
from models.project import Project
from shared.database import get_db

router = APIRouter(prefix="/api/v1/goals")

# Sprint 104: support both with and without trailing slash (frontend calls without /)
@router.get("")
@router.get("/")
def list_goals(
    project_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    matched_scenario_id: Optional[str] = Query(default=None, description="Sprint 22: 按匹配的 Scenario 过滤"),
    workflow_id: Optional[str] = Query(default=None, description="Sprint 22: 按关联的 Workflow 过滤"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """列出 Goal，支持 Sprint 22 新增字段过滤"""
    query = db.query(Goal)
    if project_id:
        subq = db.query(Project.goal_id).filter(Project.id == project_id).subquery()
        query = query.filter(Goal.id.in_(subq))
    if status:
        query = query.filter(Goal.status == status)
    if priority:
        query = query.filter(Goal.priority == priority)
    if matched_scenario_id:
        query = query.filter(Goal.matched_scenario_id == matched_scenario_id)
    if workflow_id:
        query = query.filter(Goal.workflow_id == workflow_id)

    count_q = db.query(sqla_func.count(Goal.id))
    if project_id:
        count_q = count_q.filter(Goal.id.in_(
            db.query(Project.goal_id).filter(Project.id == project_id).subquery()
        ))
    if status:
        count_q = count_q.filter(Goal.status == status)
    if priority:
        count_q = count_q.filter(Goal.priority == priority)
    if matched_scenario_id:
        count_q = count_q.filter(Goal.matched_scenario_id == matched_scenario_id)
    if workflow_id:
        count_q = count_q.filter(Goal.workflow_id == workflow_id)
    total = count_q.scalar()

    goals = query.order_by(Goal.created_at.desc()).offset(skip).limit(limit).all()
    result = []
    for g in goals:
        d = g.to_dict()
        d['matched_scenario_id'] = getattr(g, 'matched_scenario_id', None)
        d['workflow_id'] = getattr(g, 'workflow_id', None)
        result.append(d)
    return {"goals": result, "total": total, "skip": skip, "limit": limit}

@router.get("/active", response_model=List[GoalResponse])
def list_active_goals(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """列出活跃的目标（非 completed/failed）"""
    goals = db.query(Goal).filter(
        Goal.status.notin_(['completed', 'failed'])
    ).offset(skip).limit(limit).all()
    return [goal.to_dict() for goal in goals]
