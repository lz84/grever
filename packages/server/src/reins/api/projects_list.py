"""
项目列表与 Debug 端点
从 projects.py 拆分
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import Optional

from models.project import Project
from shared.database import get_db

router = APIRouter()

@router.get("/")
def list_projects(
    request: Request,
    status: Optional[str] = Query(default=None, description="按状态筛选"),
    goal_id: Optional[str] = Query(default=None, description="按目标ID过滤"),
    priority: Optional[str] = Query(default=None, description="按优先级筛选"),
    assignee: Optional[str] = Query(default=None, description="按负责人筛选"),
    workflow_id: Optional[str] = Query(default=None, description="Sprint 22: 按 Project 级 Workflow 过滤"),
    phase_order: Optional[int] = Query(default=None, description="Sprint 22: 按阶段顺序过滤"),
    matched_scenario_id: Optional[str] = Query(default=None, description="Sprint 22: 按匹配的 Scenario 过滤"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """列出所有项目，支持 Sprint 22 新增字段过滤"""
    from sqlalchemy.orm import selectinload
    query = db.query(Project).options(selectinload(Project.members))

    if status is not None:
        query = query.filter(Project.status == status)
    if goal_id is not None:
        query = query.filter(Project.goal_id == goal_id)
    if priority is not None:
        query = query.filter(Project.priority == priority)
    if assignee is not None:
        query = query.filter(Project.assignee == assignee)
    if workflow_id is not None:
        query = query.filter(Project.workflow_id == workflow_id)
    if phase_order is not None:
        query = query.filter(Project.phase_order == phase_order)
    if matched_scenario_id is not None:
        query = query.filter(Project.matched_scenario_id == matched_scenario_id)

    from sqlalchemy import func as sqla_func
    count_q = db.query(sqla_func.count(Project.id))
    if status is not None:
        count_q = count_q.filter(Project.status == status)
    if goal_id is not None:
        count_q = count_q.filter(Project.goal_id == goal_id)
    if priority is not None:
        count_q = count_q.filter(Project.priority == priority)
    if assignee is not None:
        count_q = count_q.filter(Project.assignee == assignee)
    if workflow_id is not None:
        count_q = count_q.filter(Project.workflow_id == workflow_id)
    if phase_order is not None:
        count_q = count_q.filter(Project.phase_order == phase_order)
    if matched_scenario_id is not None:
        count_q = count_q.filter(Project.matched_scenario_id == matched_scenario_id)
    total = count_q.scalar()

    projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
    return {"projects": [project.to_dict() for project in projects], "total": total, "skip": skip, "limit": limit}

@router.get("/debug-filter", tags=["debug"])
def debug_filter(
    goal_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """Debug endpoint to check goal_id filtering"""
    query = db.query(Project)
    all_count = query.count()

    if goal_id:
        filtered = query.filter(Project.goal_id == goal_id).all()
    else:
        filtered = query.all()

    return {
        "goal_id_param": goal_id,
        "total_projects": all_count,
        "filtered_count": len(filtered),
        "projects": [p.to_dict() for p in filtered]
    }
