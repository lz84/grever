"""
Sprint 61.1 Phase 2: 系统管理 Panel (Facade)

提供 Agent 重注册、任务重置、僵尸任务清理等管理端点。
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from loguru import logger
from reins.common.database import get_db
from sqlalchemy import text
from .admin_logic import _to_iso, _cleanup_zombie_tasks, _recover_agent_tasks, _log_heartbeat, _format_agent_info, _format_task_info

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

class AgentAdminInfo(BaseModel):
    id: str
    name: str
    status: str
    capabilities: list
    address: Optional[str]
    last_heartbeat: Optional[str]
    registered_at: Optional[str]
    model_name: str = ""
    task_count: int = 0

class TaskAdminInfo(BaseModel):
    id: str
    title: str
    status: str
    assigned_agent: Optional[str]
    priority: Optional[int] = 0
    updated_at: Optional[str]
    created_at: Optional[str]
    category: Optional[str] = None

class ReregisterResponse(BaseModel):
    success: bool
    agent_id: str
    message: str

class SetStatusRequest(BaseModel):
    status: str
    reason: Optional[str] = None

class SetStatusResponse(BaseModel):
    success: bool
    agent_id: str
    old_status: str
    new_status: str
    message: str

class ResetTaskResponse(BaseModel):
    success: bool
    task_id: str
    old_status: str
    message: str

class CleanupResponse(BaseModel):
    success: bool
    cleaned_count: int
    details: list

@router.get("/agents", response_model=List[AgentAdminInfo])
def list_agents_admin():
    """管理面板：获取所有 Agent + 各自任务数"""
    db = next(get_db())
    try:
        rows = db.execute(text("""
            SELECT a.id, a.name, a.status, a.capability_tags, a.address,
                   a.last_heartbeat, a.registered_at, a.model_name, COUNT(t.id) AS task_count
            FROM agents a LEFT JOIN tasks t ON t.assigned_agent = a.id
            GROUP BY a.id ORDER BY a.registered_at DESC
        """)).fetchall()

        return [_format_agent_info(row) for row in rows]
    finally:
        db.close()

@router.post("/agents/{agent_id}/reregister", response_model=ReregisterResponse)
def reregister_agent(agent_id: str):
    """重新注册 Agent"""
    db = next(get_db())
    try:
        row = db.execute(text("SELECT id, name, status FROM agents WHERE id = :aid"), {"aid": agent_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        now = datetime.now().isoformat()
        db.execute(text("""
            UPDATE agents SET status = 'online', last_heartbeat = :now, health_status = 'online',
                load = 0, current_tasks = 0, updated_at = :now WHERE id = :aid
        """), {"aid": agent_id, "now": now})
        _log_heartbeat(db, agent_id, 'online')
        db.commit()
        
        return ReregisterResponse(success=True, agent_id=agent_id, message=f"Agent '{row.name}' 已重新注册")
    finally:
        db.close()

@router.post("/agents/{agent_id}/set-status", response_model=SetStatusResponse)
def set_agent_status(agent_id: str, request: SetStatusRequest):
    """手动设置 Agent 状态"""
    db = next(get_db())
    try:
        row = db.execute(text("SELECT id, name, status FROM agents WHERE id = :aid"), {"aid": agent_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        valid_statuses = ("online", "busy", "offline", "idle")
        if request.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
        
        old_status = row.status or "unknown"
        now = datetime.now().isoformat()
        
        if request.status == "offline":
            _recover_agent_tasks(db, agent_id)
            db.execute(text("UPDATE agents SET status = :status, health_status = :status, updated_at = :now WHERE id = :aid"), {"status": request.status, "aid": agent_id, "now": now})
        else:
            load_reset = 0 if request.status == "online" else None
            if load_reset is not None:
                db.execute(text("""
                    UPDATE agents SET status = :status, health_status = :status, last_heartbeat = :now, load = :load, current_tasks = 0, updated_at = :now WHERE id = :aid
                """), {"status": request.status, "aid": agent_id, "now": now, "load": load_reset})
            else:
                db.execute(text("UPDATE agents SET status = :status, health_status = :status, updated_at = :now WHERE id = :aid"), {"status": request.status, "aid": agent_id, "now": now})
        
        db.commit()
        return SetStatusResponse(success=True, agent_id=agent_id, old_status=old_status, new_status=request.status, message=f"Agent '{row.name}' 状态: {old_status} → {request.status}")
    finally:
        db.close()

@router.post("/agents/{agent_id}/force-offline", response_model=ReregisterResponse)
def force_offline_agent(agent_id: str):
    """强制将 Agent 标记为 offline"""
    db = next(get_db())
    try:
        row = db.execute(text("SELECT id, name, status FROM agents WHERE id = :aid"), {"aid": agent_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        now = datetime.now().isoformat()
        _recover_agent_tasks(db, agent_id)
        db.execute(text("UPDATE agents SET status = 'offline', health_status = 'offline', updated_at = :now WHERE id = :aid"), {"aid": agent_id, "now": now})
        db.commit()
        
        return ReregisterResponse(success=True, agent_id=agent_id, message=f"Agent '{row.name}' 已强制下线")
    finally:
        db.close()

@router.post("/agents/{agent_id}/restart", response_model=ReregisterResponse)
def restart_agent(agent_id: str):
    """重启 Agent"""
    db = next(get_db())
    try:
        row = db.execute(text("SELECT id, name, status FROM agents WHERE id = :aid"), {"aid": agent_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        old_status = row.status or "unknown"
        now = datetime.now().isoformat()
        _recover_agent_tasks(db, agent_id)
        db.execute(text("""
            UPDATE agents SET status = 'online', last_heartbeat = :now, health_status = 'online',
                load = 0, current_tasks = 0, updated_at = :now WHERE id = :aid
        """), {"aid": agent_id, "now": now})
        _log_heartbeat(db, agent_id, 'online')
        db.commit()
        
        return ReregisterResponse(success=True, agent_id=agent_id, message=f"Agent '{row.name}' 已重启 ({old_status} → online)")
    finally:
        db.close()

@router.get("/tasks", response_model=List[TaskAdminInfo])
def list_tasks_admin(
    status: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """管理面板：获取任务列表"""
    db = next(get_db())
    try:
        conditions = []
        params = {"limit": limit, "offset": offset}
        if status:
            conditions.append("status = :status")
            params["status"] = status
        if agent_id:
            conditions.append("assigned_agent = :agent_id")
            params["agent_id"] = agent_id
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        rows = db.execute(text(f"""
            SELECT id, title, status, assigned_agent, priority, updated_at, created_at, category
            FROM tasks WHERE {where_clause} ORDER BY updated_at DESC LIMIT :limit OFFSET :offset
        """), params).fetchall()
        
        return [_format_task_info(row) for row in rows]
    finally:
        db.close()

@router.post("/tasks/{task_id}/reset", response_model=ResetTaskResponse)
def reset_task(task_id: str):
    """重置任务状态"""
    db = next(get_db())
    try:
        row = db.execute(text("SELECT id, title, status FROM tasks WHERE id = :tid"), {"tid": task_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        now = datetime.now().isoformat()
        old_status = row.status or "unknown"
        db.execute(text("""
            UPDATE tasks SET status = 'todo', assigned_agent = NULL, updated_at = :now,
                error_message = NULL, error_type = NULL, blocked_reason = NULL
            WHERE id = :tid
        """), {"tid": task_id, "now": now})
        db.commit()
        
        return ResetTaskResponse(success=True, task_id=task_id, old_status=old_status, message=f"Task '{row.title}' 已重置: {old_status} → todo")
    finally:
        db.close()

@router.post("/cleanup/zombie-tasks", response_model=CleanupResponse)
def cleanup_zombie_tasks_admin():
    """批量清理僵尸任务"""
    db = next(get_db())
    try:
        cleaned_count, details = _cleanup_zombie_tasks(db)
        return CleanupResponse(success=True, cleaned_count=cleaned_count, details=details)
    finally:
        db.close()
