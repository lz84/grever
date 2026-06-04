"""Task API review/verify endpoints — extracted from tasks.py

Contains: review_task, get_subtasks, get_parent, set_verifier,
get_effective_verifier, trigger_verification, get_verification_history,
make_ruling.
"""
from loguru import logger
import json
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.task import Task, TaskResponse
from models.project import Project
from models.goal import Goal
from reins.common.database import get_db
from reins.scheduler.result_verifier import ResultVerifier
from persistence.tables import task_activity_log

from reins.api.tasks_models import (
    ReviewTaskRequest,
    ReviewTaskResponse,
    SetVerifierRequest,
    GetEffectiveVerifierResponse,
    RulingRequest,
)
from reins.api.tasks_helpers import _get_goal_id_from_project

router = APIRouter(tags=["tasks"])

# ---- 人工审核 API ----

@router.post("/{task_id}/review", response_model=ReviewTaskResponse)
def review_task(task_id: str, request: ReviewTaskRequest, db: Session = Depends(get_db)):
    """人工审核 review_needed 状态的任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.status != "review_needed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务状态为 '{task.status}',只有 'review_needed' 状态的任务才能审核"
        )

    if request.action not in ("approve", "reject"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action 必须是 'approve' 或 'reject'"
        )

    old_status = task.status

    if request.action == "approve":
        task.status = "done"
        task.completed_at = datetime.now()
        if not task.started_at:
            task.started_at = task.completed_at
        message = "任务审核通过,已标记为完成"
    else:
        task.status = "in_progress"
        task.result_summary = None
        message = f"任务已驳回重做{',原因: ' + request.reason if request.reason else ''}"

    task.updated_at = datetime.now()

    db.execute(
        task_activity_log.insert().values(
            id=f"log-{uuid.uuid4().hex[:12]}",
            task_id=str(task_id),
            old_status=old_status,
            new_status=task.status,
            reason=f"人工审核: {request.action}" + (f" - {request.reason}" if request.reason else ""),
            timestamp=datetime.now(),
        )
    )

    db.commit()
    db.refresh(task)

    return ReviewTaskResponse(
        success=True,
        task_id=task_id,
        new_status=task.status,
        message=message,
    )

# ---- 子任务/父任务 API ----

@router.get("/{task_id}/subtasks")
def get_subtasks(task_id: str, db: Session = Depends(get_db)):
    """获取任务的子任务列表"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    subtasks = db.query(Task).filter(Task.parent_id == task_id).all()
    return {
        "task_id": task_id,
        "subtasks": [t.to_dict() for t in subtasks],
        "count": len(subtasks),
    }

@router.get("/{task_id}/parent")
def get_parent(task_id: str, db: Session = Depends(get_db)):
    """获取任务的父任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.parent_id:
        return {"task_id": task_id, "parent": None}
    parent = db.query(Task).filter(Task.id == task.parent_id).first()
    return {
        "task_id": task_id,
        "parent": parent.to_dict() if parent else None,
    }

# ---- VERIFIER AGENT API ----

@router.get("/{task_id}/verifier", response_model=GetEffectiveVerifierResponse)
def get_effective_verifier(task_id: str, db: Session = Depends(get_db)):
    """
    获取任务的有效验证 Agent(含继承链)。
    优先级: Task.verifier_agent_id → Project.verifier_agent_id → Goal.verifier_agent_id → DEFAULT_VERIFIER
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    inheritance_chain = {
        "task_verifier": task.verifier_agent_id,
        "project_verifier": None,
        "goal_verifier": None,
        "default_verifier": "3745f1f0-b67d-4287-a10b-e71b3ff17e97"
    }

    effective_verifier = task.verifier_agent_id

    if not effective_verifier and task.project_id:
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if project:
            inheritance_chain["project_verifier"] = project.verifier_agent_id
            effective_verifier = project.verifier_agent_id

    if not effective_verifier and task.project_id:
        goal_id = _get_goal_id_from_project(db, task.project_id)
        if goal_id:
            goal = db.query(Goal).filter(Goal.id == goal_id).first()
            if goal:
                inheritance_chain["goal_verifier"] = goal.verifier_agent_id
                effective_verifier = goal.verifier_agent_id

    if not effective_verifier:
        effective_verifier = "3745f1f0-b67d-4287-a10b-e71b3ff17e97"

    return GetEffectiveVerifierResponse(
        task_id=task_id,
        effective_verifier=effective_verifier,
        inheritance_chain=inheritance_chain
    )

@router.post("/{task_id}/verifier")
def set_task_verifier(task_id: str, request: SetVerifierRequest, db: Session = Depends(get_db)):
    """设置 Task 的验证 Agent ID"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.verifier_agent_id = request.verifier_agent_id
    task.updated_at = datetime.now()
    db.commit()
    db.refresh(task)

    return {"task_id": task_id, "verifier_agent_id": request.verifier_agent_id}

@router.post("/{task_id}/verify")
def trigger_verification(task_id: str, db: Session = Depends(get_db)):
    """手动触发验证(给已 verifying 的任务)"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != "verifying":
        raise HTTPException(
            status_code=400,
            detail=f"Task status is '{task.status}', expected 'verifying'"
        )

    db.commit()  # release ORM session lock

    verifier = ResultVerifier()
    result = verifier.trigger_verification(task_id, task.result or task.result_summary or "", True, task.context_md)

    return result

@router.get("/{task_id}/verifications")
def get_verification_history(task_id: str, db: Session = Depends(get_db)):
    """获取任务的验证历史记录"""
    comments = db.execute(text("""
        SELECT id, task_id, author, author_role, type, content, metadata, created_at
        FROM task_comments
        WHERE task_id = :task_id
          AND type IN ('verification', 'human_ruling')
        ORDER BY created_at ASC
    """), {"task_id": task_id}).fetchall()

    result = []
    for c in comments:
        meta = json.loads(c.metadata) if c.metadata else {}
        if c.type == "verification":
            result.append({
                "id": c.id,
                "cycle": meta.get("verification_cycle", 0),
                "type": "verification",
                "verifier": c.author,
                "passed": meta.get("passed"),
                "checks": meta.get("checks", []),
                "content": c.content,
                "created_at": str(c.created_at) if c.created_at else None
            })
        else:
            result.append({
                "id": c.id,
                "type": "human_ruling",
                "author": c.author,
                "ruling_action": meta.get("ruling_action"),
                "content": c.content,
                "created_at": str(c.created_at) if c.created_at else None
            })

    return result

@router.post("/{task_id}/ruling")
def submit_ruling(task_id: str, request: RulingRequest, db: Session = Depends(get_db)):
    """提交人工裁决(仅适用于 disputed 状态的任务)"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "disputed":
        raise HTTPException(
            status_code=400,
            detail=f"Only disputed tasks can be ruled. Current status: {task.status}"
        )

    ruling_text = request.ruling
    action = request.action

    if action not in ("done", "in_progress", "verifying"):
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")

    comment_id = f"cmt-{uuid.uuid4().hex[:8]}"
    metadata = json.dumps({"ruling_action": action})

    db.execute(text("""
        INSERT INTO task_comments (id, task_id, author, author_role, type, content, metadata, created_at)
        VALUES (:id, :task_id, :author, :author_role, :type, :content, :metadata, :created_at)
    """), {
        "id": comment_id,
        "task_id": task_id,
        "author": "human",
        "author_role": "human",
        "type": "human_ruling",
        "content": f"Human Ruling: {ruling_text}",
        "metadata": metadata,
        "created_at": datetime.now()
    })

    now = datetime.now()
    if action == "done":
        db.execute(text("""
            UPDATE tasks SET status = 'done', completed_at = :now,
                ruling_comment_id = :comment_id, verification_cycle = 0, updated_at = :now
            WHERE id = :task_id
        """), {"now": now, "comment_id": comment_id, "task_id": task_id})
    elif action == "in_progress":
        db.execute(text("""
            UPDATE tasks SET status = 'in_progress',
                ruling_comment_id = :comment_id, ruling_instruction = :ruling,
                verification_cycle = 0, updated_at = :now
            WHERE id = :task_id
        """), {"now": now, "comment_id": comment_id, "ruling": ruling_text, "task_id": task_id})
    elif action == "verifying":
        db.execute(text("""
            UPDATE tasks SET status = 'verifying',
                ruling_comment_id = :comment_id, updated_at = :now
            WHERE id = :task_id
        """), {"now": now, "comment_id": comment_id, "task_id": task_id})

    db.commit()

    return {
        "task_id": task_id,
        "status": action if action != "in_progress" else "in_progress",
        "ruling_comment_id": comment_id
    }