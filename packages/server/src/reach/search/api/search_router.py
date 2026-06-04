"""
Search Router — 全局搜索 API
从 server.py 内联端点提取（2026-05-14）
"""
from loguru import logger
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import text

from api.app_state import get_db_manager, get_reins

router = APIRouter(prefix="/api/v1", tags=["search"])

@router.get("/search")
def global_search(
    q: str = Query("", description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50, description="每类返回数量上限"),
):
    """全局搜索 - 搜索目标/项目/任务"""
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="搜索词不能为空")

    query = q.strip().lower()
    results = {"query": q, "goals": [], "projects": [], "tasks": [], "total": 0}

    # 搜索 Goals
    try:
        from reins.common.database import get_db
        from models.goal import Goal as GoalModel
        with get_db() as db:
            goals = db.query(GoalModel).all()
            matched = []
            for g in goals:
                if (query in (g.title or "").lower() or query in (g.description or "").lower()):
                    matched.append({"id": g.id, "title": g.title, "description": g.description,
                                    "status": g.status, "type": "goal"})
                    if len(matched) >= limit:
                        break
            results["goals"] = matched
            results["total"] += len(matched)
    except Exception as e:
        logger.error(f"[Search] Goals search error: {e}")

    # 搜索 Projects
    try:
        projects = get_reins().list_projects()
        matched = []
        for p in projects:
            if (query in (p.name or "").lower() or query in (p.description or "").lower()):
                matched.append({"id": p.id, "name": p.name, "description": p.description,
                                "status": p.status, "goal_id": p.goal_id, "type": "project"})
                if len(matched) >= limit:
                    break
        results["projects"] = matched
        results["total"] += len(matched)
    except Exception as e:
        logger.error(f"[Search] Projects search error: {e}")

    # 搜索 Tasks
    try:
        from reins.common.database import get_db
        from models.task import Task as TaskModel
        with get_db() as db:
            tasks = db.query(TaskModel).all()
            matched = []
            for t in tasks:
                if (query in (t.title or "").lower() or query in (t.description or "").lower()):
                    matched.append({"id": t.id, "title": t.title, "description": t.description,
                                    "status": t.status, "project_id": t.project_id,
                                    "assigned_agent": t.assigned_to, "type": "task"})
                    if len(matched) >= limit:
                        break
            results["tasks"] = matched
            results["total"] += len(matched)
    except Exception as e:
        logger.error(f"[Search] Tasks search error: {e}")

    return results
