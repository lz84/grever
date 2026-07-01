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
from sqlalchemy import func

from api.app_state import get_db_manager
from models.task import Task
from models.agent import Agent
from models.execution_log import ExecutionLog
from models.task_activity_log import TaskActivityLog

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
    row = db.query(Agent.id, Agent.status).filter(Agent.id == agent_id).first()
    if row is None:
        return False
    return True


def _record_activity(db, task_id: str, agent_id: str, action: str, detail: str, extra: Optional[dict] = None):
    """记录任务活动日志"""
    import uuid
    activity = TaskActivityLog(
        id=str(uuid.uuid4()),
        task_id=task_id,
        old_status="",
        new_status=action,
        reason=detail,
        actor=agent_id,
        timestamp=datetime.now(),
        extra=json.dumps(extra, ensure_ascii=False) if extra else None,
    )
    db.add(activity)
    db.commit()


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
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    if agent.status not in ("online", "idle"):
        raise HTTPException(
            status_code=400,
            detail=f"Agent {agent_id} is not available (status={agent.status})",
        )

    # 检查负载
    max_tasks = agent.max_concurrent_tasks or 5
    current_tasks = agent.current_tasks or 0
    if current_tasks >= max_tasks:
        raise HTTPException(
            status_code=429,
            detail=f"Agent {agent_id} is at max capacity ({current_tasks}/{max_tasks})",
        )

    # 验证任务状态
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    if task.status not in VALID_CLAIM_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} cannot be claimed (status={task.status}, "
                   f"must be one of {VALID_CLAIM_STATUSES})",
        )

    if task.assigned_agent and task.assigned_agent != agent_id:
        raise HTTPException(
            status_code=409,
            detail=f"Task {task_id} is already assigned to {task.assigned_agent}",
        )

    # 认领任务
    now = datetime.now()
    new_status = "in_progress"

    db.query(Task).filter(Task.id == task_id).update({
        'assigned_agent': agent_id,
        'status': new_status,
        'started_at': now,
        'updated_at': now,
    }, synchronize_session=False)
    db.commit()

    # 更新 Agent 当前任务数
    db.query(Agent).filter(Agent.id == agent_id).update({
        'current_tasks': Agent.current_tasks + 1,
    }, synchronize_session=False)
    db.commit()

    # 记录活动日志
    _record_activity(
        db, task_id, agent_id, "claimed",
        f"Agent {agent.name} claimed task{': ' + req.reason if req and req.reason else ''}",
        {"estimated_hours": req.estimated_hours if req else None},
    )

    logger.info(
        "Task %s claimed by agent %s (%s)",
        task_id, agent_id, agent.name,
    )

    return {
        "task_id": task_id,
        "task_title": task.title,
        "agent_id": agent_id,
        "agent_name": agent.name,
        "status": new_status,
        "claimed_at": now.isoformat(),
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
    task = db.query(Task).filter(Task.id == task_id).first()

    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    if task.assigned_agent != agent_id:
        raise HTTPException(
            status_code=403,
            detail=f"Agent {agent_id} is not assigned to task {task_id} "
                   f"(assigned to: {task.assigned_agent or 'none'})",
        )

    if req.status not in VALID_REPORT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid report status: {req.status}. Must be one of {VALID_REPORT_STATUSES}",
        )

    # 计算实际工时
    now = datetime.now()
    actual_hours = req.actual_hours
    if actual_hours is None and task.started_at:
        started = task.started_at
        if hasattr(started, 'isoformat'):
            delta = now - started
            actual_hours = round(delta.total_seconds() / 3600, 2)

    # 确定最终状态
    final_status = "completed" if req.status == "completed" else "failed"

    # 更新任务
    db.query(Task).filter(Task.id == task_id).update({
        'status': final_status,
        'result': req.result,
        'completed_at': now,
        'actual_hours': actual_hours,
        'updated_at': now,
    }, synchronize_session=False)
    db.commit()

    # 更新 Agent 当前任务数
    db.execute(
        Agent.__table__.update()
        .where(Agent.id == agent_id)
        .values(current_tasks=func.greatest(0, Agent.current_tasks - 1))
    )
    db.commit()

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
    exec_log = ExecutionLog(
        id=log_id,
        task_id=task_id,
        agent_id=agent_id,
        action='task_complete',
        input_data=None,
        output_data=req.result,
        status=final_status,
        duration_ms=int(actual_hours * 3600000) if actual_hours else 0,
        created_at=now,
        error_message=req.error_message,
        result_summary=(req.result or "")[:500] if req.result else None,
        metadata=json.dumps({
            "quality_score": req.quality_score,
            "artifacts": req.artifacts,
        }, ensure_ascii=False) if req.quality_score or req.artifacts else None,
    )
    db.add(exec_log)
    db.commit()

    logger.info(
        "Task %s reported by agent %s as %s (hours=%.2f)",
        task_id, agent_id, final_status, actual_hours or 0,
    )

    return {
        "task_id": task_id,
        "task_title": task.title,
        "agent_id": agent_id,
        "status": final_status,
        "reported_at": now.isoformat(),
        "actual_hours": actual_hours,
        "quality_score": req.quality_score,
    }
