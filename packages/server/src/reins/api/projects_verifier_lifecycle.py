"""
项目验证器、暂停/恢复端点
从 projects.py 拆分
"""
from loguru import logger
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from models.project import Project
from shared.database import get_db
from reins.scheduler.statemachine import ProjectStateMachine

router = APIRouter()

class SetProjectVerifierRequest(BaseModel):
    """设置项目验证 Agent 请求"""
    verifier_agent_id: str

@router.post("/{project_id}/verifier")
def set_project_verifier(project_id: str, request: SetProjectVerifierRequest, db: Session = Depends(get_db)):
    """设置 Project 的验证 Agent ID"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.verifier_agent_id = request.verifier_agent_id
    project.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)

    return {"project_id": project_id, "verifier_agent_id": request.verifier_agent_id}

@router.post("/{project_id}/pause")
def pause_project(project_id: str, db: Session = Depends(get_db)):
    """暂停 Project：级联暂停所有子 Task。"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status not in ('active', 'in_progress', 'running'):
        raise HTTPException(status_code=400, detail=f"Cannot pause project with status {project.status}")

    now = datetime.now(timezone.utc)
    task_rows = db.query(Task.id).filter(
        Task.project_id == project_id,
        Task.status.in_(['in_progress', 'running', 'assigned'])
    ).all()
    for (tid,) in task_rows:
        db.query(Task).filter(Task.id == tid).update({
            "status": "paused",
            "started_at": None,
            "updated_at": now,
        })

    # 使用 ProjectStateMachine 迁移状态
    fsm = ProjectStateMachine(db, project_id)
    fsm.transition("paused", reason="用户手动暂停")
    
    project.updated_at = now
    db.commit()
    return {"ok": True, "project_id": project_id, "status": "paused",
            "tasks_paused": len(task_rows)}

@router.post("/{project_id}/auto-assign")
def auto_assign_project_tasks(project_id: str, db: Session = Depends(get_db)):
    """一键分配：为项目下所有未分配的 task 自动分配 Agent。"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    task_rows = db.execute(text("""
        SELECT id FROM tasks
        WHERE project_id = :pid
          AND (assigned_agent IS NULL OR assigned_agent = '')
          AND status IN ('todo', 'pending')
    """), {"pid": project_id}).fetchall()

    if not task_rows:
        return {"ok": True, "project_id": project_id, "assigned": 0, "message": "没有未分配的任务"}

    from reins.core.assignment import get_task_assigner
    assigner = get_task_assigner()

    assigned_count = 0
    results = []
    for trow in task_rows:
        tid = trow[0]
        try:
            agent_id = assigner._select_best_agent([])
            if agent_id:
                db.query(Task).filter(Task.id == tid).update({
                    "assigned_agent": agent_id,
                    "updated_at": datetime.utcnow().isoformat(),
                })
                assigned_count += 1
                results.append({"task_id": tid, "agent_id": agent_id})
            else:
                results.append({"task_id": tid, "error": "no_available_agent"})
        except Exception as e:
            results.append({"task_id": tid, "error": str(e)})

    db.commit()
    return {"ok": True, "project_id": project_id, "assigned": assigned_count, "total": len(task_rows), "results": results}

@router.post("/{project_id}/resume")
def resume_project(project_id: str, db: Session = Depends(get_db)):
    """再激活 Project：将 paused/failed 子 Task 改回 todo。"""
    try:
        logger.info(f"[resume_project] Starting for {project_id}")
        project = db.query(Project).filter(Project.id == project_id).first()
        logger.info(f"[resume_project] project={project}, status={getattr(project, 'status', 'MISSING')}")
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        current_status = project.status
        logger.info(f"[resume_project] current_status={current_status!r}")
        if current_status != 'paused':
            raise HTTPException(status_code=400, detail=f"Cannot resume project with status {current_status}")

        now = datetime.now(timezone.utc)
        logger.info(f"[resume_project] now={now}")
        paused = db.query(Task).filter(
            Task.project_id == project_id,
            Task.status.in_(['paused', 'failed'])
        ).all()
        logger.info(f"[resume_project] paused_count={len(paused)}")
        if paused:
            db.query(Task).filter(
                Task.project_id == project_id,
                Task.status.in_(['paused', 'failed'])
            ).update({
                "status": "todo",
                "assigned_agent": None,
                "started_at": None,
                "updated_at": now,
                "result": None,
                "result_summary": None,
                "error_message": None,
                "error_type": None,
            })
            logger.info(f"[resume_project] updated {len(paused)} tasks")

        # 使用 ProjectStateMachine 迁移状态
        fsm = ProjectStateMachine(db, project_id)
        fsm.transition("active", reason="用户手动恢复")
        
        project.updated_at = now
        db.commit()
        logger.info(f"[resume_project] committed")
        return {"ok": True, "project_id": project_id, "status": "active",
                "tasks_resumed": len(paused)}
    except Exception as e:
        logger.error(f"[resume_project] ERROR: {type(e).__name__}: {e}")
        raise
