"""
任务 HITL 审批 API — Sprint 92 B92-1

POST /tasks/{task_id}/add-hitl
- 状态安全校验：仅 todo/in_progress/paused 可加 HITL
- 创建 human_input_request
- 更新 task 状态为 waiting_human
"""
import json
import uuid
from loguru import logger
from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from reins.common.database import get_db

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks-hitl"])

# Allowed states for adding HITL
ALLOWED_HITL_STATES = frozenset({"todo", "in_progress", "paused"})

# States that must reject HITL with 400
REJECT_HITL_STATES = frozenset({"done", "failed", "waiting_human", "review_needed", "timeout", "waiting"})

class AddHitlRequest(BaseModel):
    """添加 HITL 审批请求"""
    title: Optional[str] = None
    description: Optional[str] = None
    input_type: str = "approval"  # approval / confirmation / data_entry
    assigned_to: Optional[str] = None
    required_role: Optional[str] = None
    timeout_minutes: Optional[int] = None
    branches: Optional[Dict[str, str]] = None  # answer → branch mapping
    default_value: Optional[str] = None
    timeout_action: Optional[str] = None  # use_default / skip / escalate

class AddHitlResponse(BaseModel):
    """添加 HITL 响应"""
    success: bool
    task_id: str
    task_status: str
    human_input_id: str
    message: str

@router.post("/{task_id}/add-hitl", response_model=AddHitlResponse)
def add_task_hitl(task_id: str, req: AddHitlRequest, db: Session = Depends(get_db)):
    """
    为任务添加 HITL 审批。

    - 状态安全校验：todo/in_progress/paused → 允许
    - done/failed/waiting_human 等 → 400 拒绝
    - 创建 human_input_request + 更新 task 状态为 waiting_human
    - 幂等：若已有 pending HITL request，返回 409
    """
    # 1. 查询 task
    row = db.execute(text("""
        SELECT id, title, status, project_id, goal_id
        FROM tasks WHERE id = :tid
    """), {"tid": task_id}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    task_status = row[2]

    # 2. 状态安全校验
    if task_status not in ALLOWED_HITL_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"Task 状态 '{task_status}' 不允许添加 HITL。"
                   f"仅允许: {sorted(ALLOWED_HITL_STATES)}。"
                   f"状态 {sorted(REJECT_HITL_STATES)} 不允许添加。"
        )

    # 3. 幂等检查：已有 pending HITL request
    existing = db.execute(text("""
        SELECT id FROM human_input_requests
        WHERE task_id = :tid AND status = 'pending'
    """), {"tid": task_id}).fetchone()

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Task {task_id} 已有 pending 的 HITL request: {existing[0]}"
        )

    # 4. 创建 human_input_request
    input_id = f"hir-{uuid.uuid4().hex[:12]}"
    now = datetime.now()

    # Build context from task info
    context = {
        "task_title": row[1],
        "project_id": row[3],
        "goal_id": row[4],
        "previous_status": task_status,
    }

    title = req.title or f"人工审批: {row[1] or task_id}"
    description = req.description or f"任务「{row[1] or task_id}」需要人工审批"

    db.execute(text("""
        INSERT INTO human_input_requests
            (id, task_id, title, description, input_type, status,
             assigned_to, required_role,
             context, created_at, updated_at)
        VALUES (:id, :tid, :title, :desc, :itype, 'pending',
                :assigned_to, :role, :context, :now, :now)
    """), {
        "id": input_id,
        "tid": task_id,
        "title": title,
        "desc": description,
        "itype": req.input_type,
        "assigned_to": req.assigned_to,
        "role": req.required_role,
        "context": json.dumps(context),
        "now": now,
    })

    # 5. 更新 task 状态为 waiting_human
    db.execute(text("""
        UPDATE tasks SET status = 'waiting_human', updated_at = :now
        WHERE id = :tid
    """), {"now": now, "tid": task_id})

    db.commit()

    logger.info(
        "[HITL] Task %s (%s → waiting_human), request %s created",
        task_id, task_status, input_id
    )

    return AddHitlResponse(
        success=True,
        task_id=task_id,
        task_status="waiting_human",
        human_input_id=input_id,
        message=f"Task 状态已更新为 waiting_human，HITL request {input_id} 已创建",
    )
