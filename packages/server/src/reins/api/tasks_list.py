"""Task API list endpoint — extracted from tasks.py

Contains: list_tasks (GET /).
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func

from models.task import Task
from models.project import Project
from reins.common.database import get_db

from reins.api.tasks_helpers import _get_goal_id_from_project

router = APIRouter(tags=["tasks"])

# Note: FastAPI auto-redirects /tasks -> /tasks/ (307). Frontend may not follow.
# Solution: register the list endpoint twice — once via this router (with /)
# and once via the parent router (without /). See tasks.py include.
@router.get("/")
def list_tasks(
    goal_id: Optional[str] = Query(None, description="按目标 ID 过滤"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    priority: Optional[str] = Query(None),
    assigned_agent: Optional[str] = Query(None, description="按分配的 Agent 筛选"),
    workflow_step_id: Optional[str] = Query(None, description="按关联的 Workflow 节点过滤"),
    project_id: Optional[str] = Query(None, description="按项目 ID 过滤"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """列出 Task，支持按目标/项目/状态/优先级/Agent/Workflow 节点过滤。

    P5-2: category 字段已删除，由 capability_tags 替代。
    如需按标签过滤，请使用 capability_tags 相关接口。
    """
    query = db.query(Task).options(selectinload(Task.dependencies))

    subq = None
    if goal_id:
        subq = db.query(Project.id).filter(Project.goal_id == goal_id).subquery()
        query = query.filter(Task.project_id.in_(subq))
    if project_id:
        query = query.filter(Task.project_id == project_id)
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    if assigned_agent:
        query = query.filter(Task.assigned_agent == assigned_agent)
    if workflow_step_id:
        query = query.filter(Task.workflow_step_id == workflow_step_id)

    total_query = db.query(func.count(Task.id))
    if goal_id:
        total_query = total_query.filter(Task.project_id.in_(subq))
    elif project_id:
        total_query = total_query.filter(Task.project_id == project_id)
    if status:
        total_query = total_query.filter(Task.status == status)
    if priority:
        total_query = total_query.filter(Task.priority == priority)
    if assigned_agent:
        total_query = total_query.filter(Task.assigned_agent == assigned_agent)
    if workflow_step_id:
        total_query = total_query.filter(Task.workflow_step_id == workflow_step_id)
    total = total_query.scalar()

    tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    return {"tasks": [task.to_dict() for task in tasks], "total": total, "skip": skip, "limit": limit}