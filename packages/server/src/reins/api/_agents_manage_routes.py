"""Agent management routes: heartbeat_logs & trigger_mode."""
from loguru import logger
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy import text, desc, func

from api.app_state import get_db_manager
from models.agent import Agent

router = APIRouter()

@router.get("/agents/{agent_id}/heartbeat_logs")
def get_heartbeat_logs(
    agent_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """查询 Agent 心跳历史"""
    from persistence.tables import heartbeat_logs, execution_logs
    db = get_db_manager()
    try:
        with db.engine.connect() as conn:
            rows = conn.execute(
                heartbeat_logs.select()
                .where(heartbeat_logs.c.agent_id == agent_id)
                .order_by(desc(heartbeat_logs.c.timestamp)).limit(limit).offset(offset)
            ).fetchall()
            logs = [{
                "id": r.id, "agent_id": r.agent_id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "status": r.status, "latency_ms": r.latency_ms,
                "load": r.load, "current_tasks": r.current_tasks,
                "request_payload": None, "response_payload": None,
                "result_summary": None, "error_message": None,
            } for r in rows]
        try:
            with db.engine.connect() as conn2:
                exec_rows = conn2.execute(
                    execution_logs.select()
                    .where(execution_logs.c.agent_id == agent_id)
                    .where(execution_logs.c.action == 'heartbeat')
                    .order_by(desc(execution_logs.c.created_at)).limit(limit)
                ).fetchall()
                by_time = {}
                for er in exec_rows:
                    ts = er.created_at.isoformat()[:16] if er.created_at else ''
                    by_time[ts] = {"input": er.input, "output": er.output,
                                   "result_summary": er.result_summary,
                                   "error_message": er.error_message,
                                   "duration_ms": er.duration_ms}
        except Exception:
            by_time = {}
        for log in logs:
            if log["timestamp"]:
                m = by_time.get(log["timestamp"][:16])
                if m:
                    log["request_payload"] = m["input"]
                    log["response_payload"] = m["output"]
                    log["result_summary"] = m["result_summary"]
                    log["error_message"] = m["error_message"]
                    log["duration_ms"] = m["duration_ms"]
        return {"agent_id": agent_id, "logs": logs, "count": len(logs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query heartbeat logs: {e}")

@router.get("/agents/{agent_id}/load")
def get_agent_load(agent_id: str):
    """获取 Agent 当前负载（统一走 calc_dynamic_load，只算 in_progress）"""
    from reins.scheduler.load_calculator import calc_dynamic_load
    db = get_db_manager()

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    with db.engine.connect() as conn:
        dynamic_load, dynamic_tasks = calc_dynamic_load(conn, agent_id)

    max_tasks = agent.max_concurrent_tasks or 5
    return {
        "agent_id": agent.id,
        "name": agent.name,
        "load": dynamic_load,
        "current_tasks": dynamic_tasks,
        "status": agent.status,
        "trigger_mode": agent.trigger_mode,
        "poll_interval_seconds": agent.poll_interval_seconds or 10,
        "max_concurrent_tasks": max_tasks,
        "load_threshold": agent.load_threshold or 80,
        "model_name": agent.model_name or "",
        "heartbeat_load": agent.load,
        "heartbeat_current_tasks": agent.current_tasks,
    }

@router.put("/agents/{agent_id}/config")
def update_agent_config(agent_id: str, config: dict = Body(...)):
    """更新 Agent 配置（支持 capability_tags, agent_code 等字段）"""
    from api.app_state import get_db_manager
    db = get_db_manager()
    
    # Check agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    updates = {}
    
    # Update capability_tags if provided
    if "capability_tags" in config:
        ct = config["capability_tags"]
        if isinstance(ct, dict):
            from sqlalchemy import text
            ct_str = json.dumps(ct, ensure_ascii=False)
            updates["capability_tags"] = ct_str
    
    # Update agent_code if provided
    if "agent_code" in config:
        updates["agent_code"] = config["agent_code"] or None
    
    if updates:
        db.query(Agent).filter(Agent.id == agent_id).update(
            updates,
            synchronize_session="fetch"
        )
    
    return {"success": True, "agent_id": agent_id}

@router.patch("/agents/{agent_id}/trigger_mode")
def update_agent_trigger_mode(agent_id: str, mode: str = Query(default=...)):
    """更新 Agent 触发模式"""
    from models import TriggerMode
    from api.app_state import get_reins
    db = get_db_manager()
    reins = get_reins()
    if mode not in ("sse", "polling"):
        raise HTTPException(status_code=400, detail="mode must be 'sse' or 'polling'")
    agent = reins.agent_registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    old_mode = agent.trigger_mode
    agent.trigger_mode = TriggerMode(mode)
    try:
        from sqlalchemy import text
        db.query(Agent).filter(Agent.id == agent_id).update(
            {"trigger_mode": mode},
            synchronize_session="fetch"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB update failed: {e}")
    return {
        "agent_id": agent_id,
        "old_mode": old_mode.value if hasattr(old_mode, 'value') else str(old_mode),
        "new_mode": mode,
    }
