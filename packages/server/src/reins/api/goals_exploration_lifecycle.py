# -*- coding: utf-8 -*-
"""
Goal lifecycle endpoints (activate/pause/resume).
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from reins.common.database import get_db
from models import Goal, Project, Task
from models.goal import GoalStatus

router = APIRouter(prefix="/api/v1/goals", tags=["goals-exploration"])


@router.post("/{goal_id}/activate")
def activate_goal(goal_id: str, db: Session = Depends(get_db)):
    """激活目标：将状态从 draft 改为 in_progress，并触发调度器派发任务。"""
    from reins.scheduler.statemachine import GoalStateMachine
    from reins.scheduler import get_scheduler
    import asyncio

    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # 通过状态机检查并转换状态
    fsm = GoalStateMachine(db, goal_id)
    if not fsm.can_transition(GoalStatus.IN_PROGRESS):
        allowed = fsm.transition("planned", reason="激活前先transition to planned")
        if not allowed:
            raise HTTPException(status_code=400, detail=f"Cannot activate goal: {goal.status} → planned not allowed")
    
    # 再转到 in_progress
    if not fsm.can_transition(GoalStatus.IN_PROGRESS):
        raise HTTPException(status_code=400, detail=f"Cannot activate goal with status {goal.status}")
    
    fsm.transition(GoalStatus.IN_PROGRESS, reason="激活目标", extra={"updated_at": int(datetime.utcnow().timestamp())})
    
    goal = db.query(Goal).filter(Goal.id == goal_id).first()  # refresh

    if goal.mode == "research":
        raise HTTPException(status_code=400, detail="Research mode goals should use /start-iteration")

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

    db.refresh(goal)
    return {
        "id": goal.id,
        "title": goal.title,
        "status": goal.status,
        "mode": goal.mode,
    }


@router.post("/{goal_id}/pause")
def pause_goal(goal_id: str, db: Session = Depends(get_db)):
    """暂停目标：级联暂停所有子 Project 和 Task。"""
    from reins.scheduler.statemachine import GoalStateMachine

    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # 通过状态机检查
    fsm = GoalStateMachine(db, goal_id)
    if not fsm.can_transition(GoalStatus.PAUSED):
        raise HTTPException(status_code=400, detail=f"Cannot pause goal with status {goal.status}")

    # 如果当前状态不是 in_progress/active，先转到 in_progress
    if not fsm.can_transition(GoalStatus.PAUSED):
        allowed = fsm.transition("in_progress", reason="pause前需要in_progress")
        if not allowed:
            raise HTTPException(status_code=400, detail=f"Cannot pause goal: {goal.status} → in_progress not allowed")
    
    fsm.transition(GoalStatus.PAUSED, reason="暂停目标", extra={"updated_at": int(datetime.utcnow().timestamp())})
    now_ts = int(datetime.utcnow().timestamp())
    goal = db.query(Goal).filter(Goal.id == goal_id).first()  # refresh

    # Pause ALL projects under this goal (any running state)
    paused_projects = db.query(Project).filter(
        Project.goal_id == goal_id,
        Project.status.in_(['active', 'in_progress', 'running']),
    ).update({
        "status": 'paused',
        "updated_at": now_ts,
    })

    # Pause ALL tasks under this goal (via projects)
    paused_tasks = 0
    project_ids = db.query(Project.id).filter(Project.goal_id == goal_id).all()
    for (pid,) in project_ids:
        count = db.query(Task).filter(
            Task.project_id == pid,
            Task.status.in_(['in_progress', 'running', 'assigned']),
        ).update({
            "status": 'paused',
            "started_at": None,
            "updated_at": now_ts,
        })
        paused_tasks += count

    # Also pause tasks directly under the goal (no project)
    orphan_tasks = db.query(Task).filter(
        Task.goal_id == goal_id,
        Task.project_id.is_(None),
        Task.status.in_(['in_progress', 'running', 'assigned']),
    ).update({
        "status": 'paused',
        "started_at": None,
        "updated_at": now_ts,
    })
    paused_tasks += orphan_tasks

    db.commit()
    return {"ok": True, "goal_id": goal_id, "status": "paused",
            "projects_paused": paused_projects, "tasks_paused": paused_tasks}


@router.post("/{goal_id}/auto-assign")
def auto_assign_goal_tasks(goal_id: str, db: Session = Depends(get_db)):
    """一键分配：为目标下所有未分配的 task 自动分配 Agent。"""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Get all unassigned tasks under this goal (via projects or directly)
    # Tasks via projects
    task_rows = db.query(Task).with_entities(Task.id, Task.project_id).filter(
        (Project.goal_id == goal_id) | (Task.goal_id == goal_id),
        (Task.assigned_agent.is_(None) | (Task.assigned_agent == '')),
        Task.status.in_(['todo', 'pending']),
    ).all()

    if not task_rows:
        return {"ok": True, "goal_id": goal_id, "assigned": 0, "message": "没有未分配的任务"}

    from reins.core.assignment import get_task_assigner
    assigner = get_task_assigner()

    assigned_count = 0
    results = []
    now_ts = int(datetime.utcnow().timestamp())
    for tid, _ in task_rows:
        try:
            # Try to find best agent via registry
            agent_id = assigner._select_best_agent([])  # No specific capabilities required
            if agent_id:
                db.query(Task).filter(Task.id == tid).update({
                    "assigned_agent": agent_id,
                    "updated_at": now_ts,
                })
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
    from reins.scheduler.statemachine import GoalStateMachine

    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # 通过状态机检查
    fsm = GoalStateMachine(db, goal_id)
    if not fsm.can_transition(GoalStatus.IN_PROGRESS):
        raise HTTPException(status_code=400, detail=f"Cannot resume goal with status {goal.status}")

    fsm.transition(GoalStatus.IN_PROGRESS, reason="恢复目标", extra={"updated_at": int(datetime.utcnow().timestamp())})
    now_ts = int(datetime.utcnow().timestamp())
    goal = db.query(Goal).filter(Goal.id == goal_id).first()  # refresh

    # Resume ALL paused projects under this goal
    resumed_projects = db.query(Project).filter(
        Project.goal_id == goal_id,
        Project.status == 'paused',
    ).update({
        "status": 'active',
        "updated_at": now_ts,
    })

    # Resume paused + failed tasks via project_id (most common path) (most common path)
    resumed_via_project = db.query(Task).filter(
        Task.project_id.in_(
            db.query(Project.id).filter(Project.goal_id == goal_id)
        ),
        Task.status.in_(['paused', 'failed']),
    ).update({
        "status": 'todo',
        "assigned_agent": None,
        "started_at": None,
        "updated_at": now_ts,
        "result": None,
        "result_summary": None,
        "error_message": None,
        "error_type": None,
    })

    # Also resume paused + failed tasks directly under the goal (no project)
    resumed_direct = db.query(Task).filter(
        Task.goal_id == goal_id,
        Task.project_id.is_(None),
        Task.status.in_(['paused', 'failed']),
    ).update({
        "status": 'todo',
        "assigned_agent": None,
        "started_at": None,
        "updated_at": now_ts,
        "result": None,
        "result_summary": None,
        "error_message": None,
        "error_type": None,
    })

    db.commit()
    total_resumed = (resumed_via_project or 0) + (resumed_direct or 0)
    return {"ok": True, "goal_id": goal_id, "status": "in_progress",
            "projects_resumed": resumed_projects or 0, "tasks_resumed": total_resumed}