"""Pending tasks endpoint — returns all non-terminal tasks assigned to an agent."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import case

from reins.common.database import get_db
from models.agent import Agent
from models.task import Task
from models.project import Project
from models.goal import Goal

router = APIRouter()

@router.get("/agents/{agent_id}/pending-tasks")
def get_agent_pending_tasks(agent_id: str, db: Session = Depends(get_db)):
    """获取 Agent 名下所有未完成的任务（assigned_agent = xxx 且 status 不是 done/cancelled）"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 查询：归属于该 Agent 且未终态的所有任务
    priority_order = case(
        (Task.priority == 'critical', 0),
        (Task.priority == 'high', 1),
        (Task.priority == 'medium', 2),
        (Task.priority == 'low', 3),
        else_=4,
    )
    tasks = db.query(Task).filter(
        Task.assigned_agent == agent_id,
        Task.status.notin_(['done', 'cancelled'])
    ).order_by(priority_order, Task.created_at.asc()).all()

    # 批量获取 goal_id（避免 N+1）
    project_ids = list({t.project_id for t in tasks if t.project_id})
    goal_map = {}
    if project_ids:
        projects = db.query(Project).filter(Project.id.in_(project_ids)).all()
        goal_map = {p.id: p.goal_id for p in projects}

    result = []
    for task in tasks:
        goal_id = goal_map.get(task.project_id)
        result.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "goal_id": str(goal_id) if goal_id else (task.goal_id or None),
            "status": task.status,
            "priority": task.priority,
            "assigned_agent": task.assigned_agent,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "capability_tags": task.capability_tags,
            "needs_verification": task.needs_verification,
            "verifier_agent_id": task.verifier_agent_id,
            "paused_reason": getattr(task, 'paused_reason', None),
            "error_message": task.error_message,
            "result_summary": task.result_summary,
        })

    return {
        "success": True,
        "agent_id": agent_id,
        "pending_tasks": result,
        "total_count": len(result),
    }
