# -*- coding: utf-8 -*-
"""
Goal lifecycle endpoints (activate/pause/resume).
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from reins.common.database import get_db
from models.goal import GoalStatus

router = APIRouter(prefix="/api/v1/goals", tags=["goals-exploration"])

@router.post("/{goal_id}/activate")
def activate_goal(goal_id: str, db: Session = Depends(get_db)):
    """激活目标：将状态从 draft 改为 in_progress，并触发调度器派发任务。"""
    from reins.scheduler import get_scheduler
    import asyncio

    row = db.execute(
        text("SELECT id, mode, status FROM goals WHERE id = :id"),
        {"id": goal_id}
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Goal not found")
    if row.get("status") in ("in_progress", "active"):
        raise HTTPException(status_code=400, detail="Goal already active")
    if row.get("mode") == "exploration":
        raise HTTPException(status_code=400, detail="Exploration mode goals should use /start-iteration")

    db.execute(
        text("UPDATE goals SET status = 'in_progress', updated_at = :now WHERE id = :id"),
        {"now": int(datetime.utcnow().timestamp()), "id": goal_id}
    )
    db.commit()

    try:
        sched = get_scheduler()
        if sched:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(sched._tick())
            finally:
                loop.close()
    except Exception:
        pass

    updated = db.execute(
        text("SELECT id, title, status, mode, created_at FROM goals WHERE id = :id"),
        {"id": goal_id}
    ).mappings().fetchone()

    return {
        "id": updated["id"],
        "title": updated["title"],
        "status": updated["status"],
        "mode": updated["mode"],
    }

@router.post("/{goal_id}/pause")
def pause_goal(goal_id: str, db: Session = Depends(get_db)):
    """暂停目标：级联暂停所有子 Project 和 Task。"""
    row = db.execute(text("SELECT id, status FROM goals WHERE id = :id"), {"id": goal_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Goal not found")
    if row[1] not in (GoalStatus.IN_PROGRESS, 'active'):
        raise HTTPException(status_code=400, detail=f"Cannot pause goal with status {row[1]}")

    now = int(datetime.utcnow().timestamp())
    db.execute(text("UPDATE goals SET status=:s, updated_at=:now WHERE id=:id"),
               {"s": GoalStatus.PAUSED, "now": now, "id": goal_id})

    # Pause ALL projects under this goal (any running state)
    proj_rows = db.execute(text(
        "SELECT id FROM projects WHERE goal_id=:gid AND status IN ('active','in_progress','running')"
    ), {"gid": goal_id}).fetchall()
    paused_projects = 0
    paused_tasks = 0
    for prow in proj_rows:
        pid = prow[0]
        db.execute(text("UPDATE projects SET status='paused', updated_at=:now WHERE id=:pid"),
                   {"now": now, "pid": pid})
        paused_projects += 1
        # Pause ALL tasks under this project (any running state)
        task_rows = db.execute(text(
            "SELECT id FROM tasks WHERE project_id=:pid AND status IN ('in_progress','running','assigned')"
        ), {"pid": pid}).fetchall()
        for trow in task_rows:
            tid = trow[0]
            db.execute(text(
                "UPDATE tasks SET status='paused', started_at=NULL, updated_at=:now WHERE id=:tid"
            ), {"now": now, "tid": tid})
            paused_tasks += 1

    # Also pause tasks directly under the goal (no project)
    orphan_tasks = db.execute(text(
        "SELECT id FROM tasks WHERE goal_id=:gid AND project_id IS NULL AND status IN ('in_progress','running','assigned')"
    ), {"gid": goal_id}).fetchall()
    for trow in orphan_tasks:
        tid = trow[0]
        db.execute(text(
            "UPDATE tasks SET status='paused', started_at=NULL, updated_at=:now WHERE id=:tid"
        ), {"now": now, "tid": tid})
        paused_tasks += 1

    db.commit()
    return {"ok": True, "goal_id": goal_id, "status": "paused",
            "projects_paused": paused_projects, "tasks_paused": paused_tasks}

@router.post("/{goal_id}/auto-assign")
def auto_assign_goal_tasks(goal_id: str, db: Session = Depends(get_db)):
    """一键分配：为目标下所有未分配的 task 自动分配 Agent。"""
    row = db.execute(text("SELECT id, status FROM goals WHERE id = :id"), {"id": goal_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Get all unassigned tasks under this goal (via projects or directly)
    task_rows = db.execute(text("""
        SELECT t.id, t.project_id
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
        WHERE (p.goal_id = :gid OR t.goal_id = :gid)
          AND (t.assigned_agent IS NULL OR t.assigned_agent = '')
          AND t.status IN ('todo', 'pending')
    """), {"gid": goal_id}).fetchall()

    if not task_rows:
        return {"ok": True, "goal_id": goal_id, "assigned": 0, "message": "没有未分配的任务"}

    from reins.core.assignment import get_task_assigner
    assigner = get_task_assigner()

    assigned_count = 0
    results = []
    for trow in task_rows:
        tid = trow[0]
        try:
            # Try to find best agent via registry
            agent_id = assigner._select_best_agent([])  # No specific capabilities required
            if agent_id:
                db.execute(text(
                    "UPDATE tasks SET assigned_agent = :aid, updated_at = :now WHERE id = :tid"
                ), {"aid": agent_id, "now": int(datetime.utcnow().timestamp()), "tid": tid})
                assigned_count += 1
                results.append({"task_id": tid, "agent_id": agent_id})
            else:
                results.append({"task_id": tid, "error": "no_available_agent"})
        except Exception as e:
            results.append({"task_id": tid, "error": str(e)})

    db.commit()
    return {"ok": True, "goal_id": goal_id, "assigned": assigned_count, "total": len(task_rows), "results": results}

@router.post("/{goal_id}/resume")
def resume_goal(goal_id: str, db: Session = Depends(get_db)):
    """再激活目标：恢复所有子 Project 为 active，Paused/Failed 的 Task 改回 todo 重新派发。"""
    row = db.execute(text("SELECT id, status FROM goals WHERE id = :id"), {"id": goal_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Goal not found")
    if row[1] != GoalStatus.PAUSED:
        raise HTTPException(status_code=400, detail=f"Cannot resume goal with status {row[1]}")

    now = int(datetime.utcnow().timestamp())
    db.execute(text("UPDATE goals SET status=:s, updated_at=:now WHERE id=:id"),
               {"s": GoalStatus.IN_PROGRESS, "now": now, "id": goal_id})

    # Resume ALL paused projects under this goal
    resumed_projects = db.execute(text(
        "UPDATE projects SET status='active', updated_at=:now WHERE goal_id=:gid AND status='paused'"
    ), {"now": now, "gid": goal_id}).rowcount

    # Resume paused + failed tasks via project_id (most common path)
    resumed_via_project = db.execute(text(
        "UPDATE tasks SET status='todo', assigned_agent=NULL, started_at=NULL, updated_at=:now, "
        "result=NULL, result_summary=NULL, error_message=NULL, error_type=NULL "
        "WHERE project_id IN (SELECT id FROM projects WHERE goal_id=:gid) AND status IN ('paused','failed')"
    ), {"now": now, "gid": goal_id}).rowcount

    # Also resume paused + failed tasks directly under the goal (no project)
    resumed_direct = db.execute(text(
        "UPDATE tasks SET status='todo', assigned_agent=NULL, started_at=NULL, updated_at=:now, "
        "result=NULL, result_summary=NULL, error_message=NULL, error_type=NULL "
        "WHERE goal_id=:gid AND project_id IS NULL AND status IN ('paused','failed')"
    ), {"now": now, "gid": goal_id}).rowcount

    db.commit()
    total_resumed = (resumed_via_project or 0) + (resumed_direct or 0)
    return {"ok": True, "goal_id": goal_id, "status": "in_progress",
            "projects_resumed": resumed_projects or 0, "tasks_resumed": total_resumed}