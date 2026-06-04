"""
Agent Task Operations API

提供 Agent 主动认领任务和上报结果端点。
"""

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from api.app_state import get_db_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agents", tags=["agent-task-operations"])

# ===========================================================================
# 请求/响应模型
# ===========================================================================


class ClaimRequest(BaseModel):
    """认领任务请求"""
    reason: Optional[str] = None
    estimated_hours: Optional[float] = None


class ReportRequest(BaseModel):
    """上报任务结果请求"""
    status: str = "completed"  # completed / failed / partial
    result: Optional[str] = None
    error_message: Optional[str] = None
    actual_hours: Optional[float] = None
    quality_score: Optional[float] = None
    artifacts: Optional[list[dict]] = None


class ClaimResponse(BaseModel):
    task_id: str
    agent_id: str
    status: str
    claimed_at: str


class ReportResponse(BaseModel):
    task_id: str
    agent_id: str
    status: str
    reported_at: str


# ===========================================================================
# 辅助函数
# ===========================================================================

VALID_CLAIM_STATUSES = {"todo", "pending", "unassigned"}
VALID_REPORT_STATUSES = {"completed", "failed", "partial"}


def _verify_agent_exists(db, agent_id: str) -> bool:
    """验证 Agent 是否存在"""
    with db.engine.connect() as conn:
        row = row = conn.execute(
        text("SELECT id, status FROM agents WHERE id = :id"),
        {"id": agent_id},
        ).fetchone()
    if row is None:
        return False
    return True


def _record_activity(db, task_id: str, agent_id: str, action: str, detail: str, extra: Optional[dict] = None):
    """记录任务活动日志"""
    import uuid
    activity_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    with db.engine.connect() as conn:
        conn.execute(
        text("""
        INSERT INTO task_activity_log (
        id, task_id, old_status, new_status, reason, actor, timestamp, extra
        ) VALUES (
        :id, :task_id, '', :new_status, :reason, :actor, :timestamp, :extra
        )
        """),
        {
        "id": activity_id,
        "task_id": task_id,
        "new_status": action,
        "reason": detail,
        "actor": agent_id,
        "timestamp": now,
        "extra": json.dumps(extra, ensure_ascii=False) if extra else None,
        },
        )
        conn.commit()


# ===========================================================================
# POST /api/v1/agents/{agent_id}/tasks/{task_id}/claim — 认领任务
# ===========================================================================

@router.post("/{agent_id}/tasks/{task_id}/claim")
def claim_task(agent_id: str, task_id: str, req: Optional[ClaimRequest] = None):
    """
    Agent 主动认领任务。

    - 验证 Agent 存在且在线
    - 验证任务状态允许认领
    - 更新任务的 assigned_agent 和状态
    """
    db = get_db_manager()

    # 验证 Agent 存在
    with db.engine.connect() as conn:
        agent_row = agent_row = conn.execute(
        text("SELECT id, name, status, current_tasks, max_concurrent_tasks FROM agents WHERE id = :id"),
        {"id": agent_id},
        ).fetchone()

    if agent_row is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    if agent_row.status not in ("online", "idle"):
        raise HTTPException(
            status_code=400,
            detail=f"Agent {agent_id} is not available (status={agent_row.status})",
        )

    # 检查负载
    max_tasks = agent_row.max_concurrent_tasks or 5
    current_tasks = agent_row.current_tasks or 0
    if current_tasks >= max_tasks:
        raise HTTPException(
            status_code=429,
            detail=f"Agent {agent_id} is at max capacity ({current_tasks}/{max_tasks})",
        )

    # 验证任务状态
    with db.engine.connect() as conn:
        task_row = task_row = conn.execute(
        text("SELECT id, title, status, assigned_agent, project_id FROM tasks WHERE id = :id"),
        {"id": task_id},
        ).fetchone()

    if task_row is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    if task_row.status not in VALID_CLAIM_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} cannot be claimed (status={task_row.status}, "
                   f"must be one of {VALID_CLAIM_STATUSES})",
        )

    if task_row.assigned_agent and task_row.assigned_agent != agent_id:
        raise HTTPException(
            status_code=409,
            detail=f"Task {task_id} is already assigned to {task_row.assigned_agent}",
        )

    # 认领任务
    now = datetime.now().isoformat()
    new_status = "in_progress"

    with db.engine.connect() as conn:
        conn.execute(
        text("""
        UPDATE tasks SET
        assigned_agent = :agent_id,
        status = :status,
        started_at = :started_at,
        updated_at = :updated_at
        WHERE id = :id
        """),
        {
        "agent_id": agent_id,
        "status": new_status,
        "started_at": now,
        "updated_at": now,
        "id": task_id,
        },
        )
        conn.commit()

    # 更新 Agent 当前任务数
    with db.engine.connect() as conn:
        conn.execute(
        text("UPDATE agents SET current_tasks = current_tasks + 1 WHERE id = :id"),
        {"id": agent_id},
        )
        conn.commit()

    # 记录活动日志
    _record_activity(
        db, task_id, agent_id, "claimed",
        f"Agent {agent_row.name} claimed task{': ' + req.reason if req and req.reason else ''}",
        {"estimated_hours": req.estimated_hours if req else None},
    )

    logger.info(
        "Task %s claimed by agent %s (%s)",
        task_id, agent_id, agent_row.name,
    )

    return {
        "task_id": task_id,
        "task_title": task_row.title,
        "agent_id": agent_id,
        "agent_name": agent_row.name,
        "status": new_status,
        "claimed_at": now,
    }


# ===========================================================================
# POST /api/v1/agents/{agent_id}/tasks/{task_id}/report — 上报任务结果
# ===========================================================================

@router.post("/{agent_id}/tasks/{task_id}/report")
def report_task(agent_id: str, task_id: str, req: ReportRequest):
    """
    Agent 上报任务执行结果。

    - 验证 Agent 是任务的执行者
    - 更新任务状态和结果
    - 记录执行日志
    - 更新 Agent 负载
    """
    db = get_db_manager()

    # 验证 Agent 存在
    if not _verify_agent_exists(db, agent_id):
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    # 验证任务存在且由该 Agent 执行
    with db.engine.connect() as conn:
        task_row = task_row = conn.execute(
        text("""
        SELECT id, title, status, assigned_agent, project_id,
        started_at, estimated_hours
        FROM tasks WHERE id = :id
        """),
        {"id": task_id},
        ).fetchone()

    if task_row is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    if task_row.assigned_agent != agent_id:
        raise HTTPException(
            status_code=403,
            detail=f"Agent {agent_id} is not assigned to task {task_id} "
                   f"(assigned to: {task_row.assigned_agent or 'none'})",
        )

    if req.status not in VALID_REPORT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid report status: {req.status}. Must be one of {VALID_REPORT_STATUSES}",
        )

    # 计算实际工时
    now = datetime.now()
    actual_hours = req.actual_hours
    if actual_hours is None and task_row.started_at:
        started = task_row.started_at
        if hasattr(started, 'isoformat'):
            delta = now - started
            actual_hours = round(delta.total_seconds() / 3600, 2)

    # 确定最终状态
    final_status = "completed" if req.status == "completed" else "failed"

    # 更新任务
    with db.engine.connect() as conn:
        conn.execute(
        text("""
        UPDATE tasks SET
        status = :status,
        result = :result,
        completed_at = :completed_at,
        actual_hours = :actual_hours,
        updated_at = :updated_at
        WHERE id = :id
        """),
        {
        "status": final_status,
        "result": req.result,
        "completed_at": now.isoformat(),
        "actual_hours": actual_hours,
        "updated_at": now.isoformat(),
        "id": task_id,
        },
        )
        conn.commit()

    # 更新 Agent 当前任务数
    with db.engine.connect() as conn:
        conn.execute(
        text("UPDATE agents SET current_tasks = MAX(0, current_tasks - 1) WHERE id = :id"),
        {"id": agent_id},
        )
        conn.commit()

    # 记录活动日志
    _record_activity(
        db, task_id, agent_id, "reported",
        f"Task reported as {final_status}{': ' + req.error_message if req.error_message else ''}",
        {
            "quality_score": req.quality_score,
            "actual_hours": actual_hours,
            "artifacts_count": len(req.artifacts) if req.artifacts else 0,
        },
    )

    # 记录执行日志
    import uuid
    log_id = str(uuid.uuid4())
    with db.engine.connect() as conn:
        conn.execute(
        text("""
        INSERT INTO execution_logs (
        id, task_id, agent_id, action, input, output, status,
        duration_ms, created_at, error_message, result_summary, metadata
        ) VALUES (
        :id, :task_id, :agent_id, 'task_complete', :input, :output, :status,
        :duration_ms, :created_at, :error_message, :result_summary, :metadata
        )
        """),
        {
        "id": log_id,
        "task_id": task_id,
        "agent_id": agent_id,
        "input": None,
        "output": req.result,
        "status": final_status,
        "duration_ms": int(actual_hours * 3600000) if actual_hours else 0,
        "created_at": now.isoformat(),
        "error_message": req.error_message,
        "result_summary": (req.result or "")[:500] if req.result else None,
        "metadata": json.dumps({
        "quality_score": req.quality_score,
        "artifacts": req.artifacts,
        }, ensure_ascii=False) if req.quality_score or req.artifacts else None,
        },
        )
        conn.commit()

    logger.info(
        "Task %s reported by agent %s as %s (hours=%.2f)",
        task_id, agent_id, final_status, actual_hours or 0,
    )

    return {
        "task_id": task_id,
        "task_title": task_row.title,
        "agent_id": agent_id,
        "status": final_status,
        "reported_at": now.isoformat(),
        "actual_hours": actual_hours,
        "quality_score": req.quality_score,
    }
