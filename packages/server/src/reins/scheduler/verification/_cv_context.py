"""Context collection for coordination verification."""
import json
from typing import Any, Dict, Optional

from loguru import logger
from models.task import Task, TaskStatus
from models.project import Project
from models.goal import Goal
from models.planning_session import PlanningSession


def _safe_json(value: Any, default: Any = None) -> Any:
    """安全解析 JSON 字符串。"""
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def collect_context(target_id: str, level: str, session) -> Optional[Dict[str, Any]]:
    """收集 Project 或 Goal 的完整上下文。"""
    if level == "project":
        return _collect_project_context(target_id, session)
    elif level == "goal":
        return _collect_goal_context(target_id, session)
    return None


def _collect_project_context(project_id: str, session) -> Dict[str, Any]:
    """收集 Project 上下文。"""
    project = session.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None

    tasks = session.query(Task).filter(
        Task.project_id == project_id, Task.status != TaskStatus.TODO
    ).all()

    task_results = [{
        "id": t.id, "title": t.title, "status": t.status,
        "result_summary": t.result_summary or "", "result": t.result or "",
        "capability_tags": _safe(t.capability_tags, {}),
        "verification_round": getattr(t, "verification_round", 0),
        "verification_cycle": getattr(t, "verification_cycle", 0),
    } for t in tasks]

    planning_history = []
    if project.goal_id:
        for ps in session.query(PlanningSession).filter(
            PlanningSession.goal_id == project.goal_id
        ).all():
            planning_history.append({
                "id": ps.id, "status": ps.status,
                "discussion_log": _safe(ps.discussion_log, []),
                "confirmed_plan": _safe(ps.confirmed_plan, {}),
            })

    return {
        "type": "project",
        "project": {
            "id": project.id, "name": project.name, "description": project.description,
            "goal_id": project.goal_id, "status": project.status,
            "capability_tags": _safe(project.capability_tags, {}),
            "context_md": getattr(project, "context_md", None),
        },
        "tasks": task_results, "planning_sessions": planning_history,
        "all_tasks_done": all(t.status == TaskStatus.DONE for t in tasks),
        "total_tasks": len(tasks), "done_tasks": sum(1 for t in tasks if t.status == TaskStatus.DONE),
    }


def _collect_goal_context(goal_id: str, session) -> Dict[str, Any]:
    """收集 Goal 上下文。"""
    goal = session.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        return None

    projects = session.query(Project).filter(Project.goal_id == goal_id).all()
    project_results = []
    for p in projects:
        tasks = session.query(Task).filter(
            Task.project_id == p.id, Task.status != TaskStatus.TODO
        ).all()
        project_results.append({
            "id": p.id, "name": p.name, "status": p.status,
            "total_tasks": len(tasks),
            "done_tasks": sum(1 for t in tasks if t.status == TaskStatus.DONE),
            "tasks": [{"id": t.id, "title": t.title, "status": t.status,
                       "result_summary": t.result_summary or ""} for t in tasks],
        })

    planning_history = []
    for ps in session.query(PlanningSession).filter(
        PlanningSession.goal_id == goal_id
    ).all():
        planning_history.append({
            "id": ps.id, "status": ps.status,
            "discussion_log": _safe(ps.discussion_log, []),
            "confirmed_plan": _safe(ps.confirmed_plan, {}),
        })

    all_done = all(
        p.status in ("completed", "active") and _all_tasks_done(p.id, session)
        for p in projects
    )

    return {
        "type": "goal",
        "goal": {
            "id": goal.id, "title": goal.title, "description": goal.description,
            "status": goal.status, "progress": getattr(goal, "progress", 0.0),
            "capability_tags": _safe(goal.capability_tags, {}),
            "context_md": getattr(goal, "context_md", None),
        },
        "projects": project_results, "planning_sessions": planning_history,
        "all_projects_completed": all_done, "total_projects": len(projects),
    }


def _all_tasks_done(project_id: str, session) -> bool:
    """检查 Project 下所有非 canceled Task 是否均为 done。"""
    tasks = session.query(Task).filter(
        Task.project_id == project_id,
        Task.status.notin_([TaskStatus.TODO, TaskStatus.CANCELED]),
    ).all()
    return all(t.status == TaskStatus.DONE for t in tasks)
