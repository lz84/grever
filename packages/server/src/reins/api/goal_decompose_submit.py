"""
目标分解提交端点
从 goal_decompose.py 拆分出的 submit 模块
"""
import uuid
from loguru import logger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session

from shared.database import get_db_session
from models.goal import Goal
from models.project import Project
from models.task import Task

router = APIRouter()

@router.post("/{goal_id}/assign-tasks")
def assign_goal_tasks(goal_id: str):
    """一键分配目标下所有未分配任务（调用匹配引擎）"""
    db = next(get_db_session())
    try:
        from reins.scheduler.task_assigner import TaskAssigner
        from persistence.database import DatabaseManager
        from persistence.base import DatabaseConfig

        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            raise HTTPException(status_code=404, detail={"error": "GOAL_NOT_FOUND", "message": "Goal not found"})

        # 获取目标下所有待分配任务
        project_ids = [p.id for p in db.query(Project).filter(Project.goal_id == goal_id).all()]
        if not project_ids:
            return {"success": False, "message": "目标下无项目", "assigned_count": 0}

        import os
        db_path = os.environ.get("SQLITE_PATH", r"D:\work\research\agents-nexus\data\reins.db")
        db_manager = DatabaseManager(DatabaseConfig(provider="sqlite", path=db_path))
        assigner = TaskAssigner(db_manager)
        result = assigner.assign_pending_tasks()

        # 过滤只统计该目标下的任务
        assigned_count = db.query(Task).filter(
            Task.project_id.in_(project_ids),
            Task.assigned_agent != None,
            Task.status == 'in_progress'
        ).count()

        return {"success": True, "goal_id": goal_id, "assigned_count": assigned_count}
    finally:
        db.close()

@router.post("/projects/{project_id}/assign-tasks")
def assign_project_tasks(project_id: str):
    """一键分配项目下所有未分配任务（调用匹配引擎）"""
    db = next(get_db_session())
    try:
        from reins.scheduler.task_assigner import TaskAssigner
        from persistence.database import DatabaseManager
        from persistence.base import DatabaseConfig

        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail={"error": "PROJECT_NOT_FOUND", "message": "Project not found"})

        import os
        db_path = os.environ.get("SQLITE_PATH", r"D:\work\research\agents-nexus\data\reins.db")
        db_manager = DatabaseManager(DatabaseConfig(provider="sqlite", path=db_path))
        assigner = TaskAssigner(db_manager)
        result = assigner.assign_pending_tasks()

        # 统计该项目下已分配任务
        assigned_count = db.query(Task).filter(
            Task.project_id == project_id,
            Task.assigned_agent != None,
            Task.status == 'in_progress'
        ).count()

        return {"success": True, "project_id": project_id, "assigned_count": assigned_count}
    finally:
        db.close()

class SubmitProjectRequest(BaseModel):
    """用户编辑后提交的项目"""
    model_config = {"extra": "ignore"}
    name: str
    description: str = ""
    priority: int = 3  # 1=P0, 2=P1, 3=P2, 4=P3

class SubmitDecomposeBody(BaseModel):
    model_config = {"extra": "ignore"}
    projects: List[SubmitProjectRequest]

PRIORITY_MAP = {
    1: "high",
    2: "medium",
    3: "medium",
    4: "low",
}

@router.post("/{goal_id}/decompose/submit")
def submit_decomposed_projects(
    goal_id: str,
    body: SubmitDecomposeBody,
):
    """提交用户编辑后的分解项目

    Sprint 85 增强：分解完成后不触发自动分配，
    由 TaskAssigner.assign_pending_tasks() 统一处理。
    """
    db = next(get_db_session())

    try:
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")

        if not body.projects:
            raise HTTPException(status_code=400, detail="项目列表为空")

        created_projects = []
        for proj_data in body.projects:
            priority_str = PRIORITY_MAP.get(proj_data.priority, "medium")

            project = Project(
                id=f"project-{uuid.uuid4().hex[:12]}",
                name=proj_data.name,
                description=proj_data.description,
                priority=priority_str,
                goal_id=goal.id,
                status="active",
            )
            db.add(project)
            db.flush()
            db.refresh(project)
            created_projects.append(project)

        db.commit()

        # Sprint 85: 不在此处同步触发分配，由调度器后台统一处理
        # assign_pending_tasks() 会遍历所有 capability_tags 完备的待分配任务
        # 如需立即触发，可调用 POST /scheduler/assign

        project_responses = [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "priority": p.priority,
                "status": p.status,
                "goal_id": p.goal_id,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in created_projects
        ]

        return {
            "success": True,
            "goal_id": goal_id,
            "goal_title": goal.title,
            "project_count": len(project_responses),
            "projects": project_responses,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")
    finally:
        if db:
            db.close()
