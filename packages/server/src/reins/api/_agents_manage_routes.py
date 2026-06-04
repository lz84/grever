"""Agent management routes: heartbeat_logs & trigger_mode."""
from loguru import logger
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy import text, desc

from api.app_state import get_db_manager

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
    """获取 Agent 当前负载（根据待处理任务动态计算）"""
    from persistence.tables import agents as agents_table
    db = get_db_manager()
    with db.engine.connect() as conn:
        # 先查 Agent 配置
        row = conn.execute(
            text("SELECT id, name, load, current_tasks, status, trigger_mode, "
                 "poll_interval_seconds, max_concurrent_tasks, load_threshold, "
                 "model_name, registered_at, last_heartbeat "
                 "FROM agents WHERE id = :id"),
            {"id": agent_id}
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")

        # 动态计算：统计实际待处理任务数
        pending_count = conn.execute(
            text("SELECT COUNT(*) FROM tasks "
                 "WHERE assigned_agent = :aid "
                 "AND status IN ('todo', 'in_progress', 'pending', 'paused', 'waiting')"),
            {"aid": agent_id}
        ).scalar() or 0

        max_tasks = row.max_concurrent_tasks or 1
        # 负载百分比 = min(100, 待处理数/最大并发 * 100)
        dynamic_load = min(100, round(pending_count / max_tasks * 100))

        return {
            "agent_id": row.id,
            "name": row.name,
            "load": dynamic_load,
            "current_tasks": pending_count,
            "status": row.status,
            "trigger_mode": row.trigger_mode,
            "poll_interval_seconds": row.poll_interval_seconds,
            "max_concurrent_tasks": max_tasks,
            "load_threshold": row.load_threshold,
            "model_name": row.model_name,
            # 保留原始心跳上报值，前端可选展示
            "heartbeat_load": row.load,
            "heartbeat_current_tasks": row.current_tasks,
        }

@router.put("/agents/{agent_id}/config")
def update_agent_config(agent_id: str, config: dict = Body(...)):
    """更新 Agent 配置（支持 capability_tags 等字段）"""
    db = get_db_manager()
    with db.engine.begin() as conn:
        # Check agent exists
        row = conn.execute(text("SELECT id FROM agents WHERE id = :id"), {"id": agent_id}).first()
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
        # Update capability_tags if provided
        if "capability_tags" in config:
            ct = config["capability_tags"]
            if isinstance(ct, dict):
                ct_str = json.dumps(ct, ensure_ascii=False)
                conn.execute(text(
                    "UPDATE agents SET capability_tags = :ct WHERE id = :id"
                ), {"ct": ct_str, "id": agent_id})
        return {"success": True, "agent_id": agent_id}

@router.patch("/agents/{agent_id}/trigger_mode")
def update_agent_trigger_mode(agent_id: str, mode: str = Query(default=...)):
    """更新 Agent 触发模式"""
    from persistence.tables import agents as agents_table
    from models import TriggerMode
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
        with db.engine.begin() as conn:
            conn.execute(agents_table.update()
                .where(agents_table.c.id == agent_id).values(trigger_mode=mode))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB update failed: {e}")
    return {
        "agent_id": agent_id,
        "old_mode": old_mode.value if hasattr(old_mode, 'value') else str(old_mode),
        "new_mode": mode,
    }
