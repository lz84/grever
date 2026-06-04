"""Admin Logic Module"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import text

def _to_iso(val) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    return str(val)

def _cleanup_zombie_tasks(db) -> Tuple[int, List[str]]:
    """批量清理僵尸任务"""
    details = []
    total_cleaned = 0
    now = datetime.now().isoformat()

    result = db.execute(text("""
        SELECT id, title, assigned_agent FROM tasks
        WHERE status = 'in_progress' AND assigned_agent IS NOT NULL
        AND assigned_agent NOT IN (SELECT id FROM agents)
    """)).fetchall()
    if result:
        ids = [r[0] for r in result]
        placeholders = ",".join([f":tid{i}" for i in range(len(ids))])
        params = {f"tid{i}": ids[i] for i in range(len(ids))}
        params["now"] = now
        db.execute(text(f"UPDATE tasks SET status = 'todo', assigned_agent = NULL, updated_at = :now WHERE id IN ({placeholders})"), params)
        details.append(f"孤立任务: {len(ids)} 个 (assigned_agent 不存在)")
        total_cleaned += len(ids)

    result2 = db.execute(text("""
        SELECT id, title FROM tasks
        WHERE status = 'verifying' AND updated_at < datetime('now', '-1 hour')
    """)).fetchall()
    if result2:
        ids2 = [r[0] for r in result2]
        placeholders2 = ",".join([f":tid{i}" for i in range(len(ids2))])
        params2 = {f"tid{i}": ids2[i] for i in range(len(ids2))}
        params2["now"] = now
        db.execute(text(f"UPDATE tasks SET status = 'todo', assigned_agent = NULL, updated_at = :now WHERE id IN ({placeholders2})"), params2)
        details.append(f"verifying 僵尸: {len(ids2)} 个 (超时 1h)")
        total_cleaned += len(ids2)

    result3 = db.execute(text("""
        SELECT id, title FROM tasks
        WHERE status IN ('blocked', 'timeout') AND updated_at < datetime('now', '-24 hours')
    """)).fetchall()
    if result3:
        ids3 = [r[0] for r in result3]
        placeholders3 = ",".join([f":tid{i}" for i in range(len(ids3))])
        params3 = {f"tid{i}": ids3[i] for i in range(len(ids3))}
        params3["now"] = now
        db.execute(text(f"UPDATE tasks SET status = 'todo', assigned_agent = NULL, updated_at = :now WHERE id IN ({placeholders3})"), params3)
        details.append(f"blocked/timeout 僵尸: {len(ids3)} 个 (超时 24h)")
        total_cleaned += len(ids3)

    result4 = db.execute(text("""
        SELECT id, title FROM tasks
        WHERE status = 'in_progress' AND assigned_agent IN (SELECT id FROM agents WHERE status = 'offline')
    """)).fetchall()
    if result4:
        ids4 = [r[0] for r in result4]
        placeholders4 = ",".join([f":tid{i}" for i in range(len(ids4))])
        params4 = {f"tid{i}": ids4[i] for i in range(len(ids4))}
        params4["now"] = now
        db.execute(text(f"UPDATE tasks SET status = 'todo', assigned_agent = NULL, updated_at = :now WHERE id IN ({placeholders4})"), params4)
        details.append(f"offline agent 任务: {len(ids4)} 个")
        total_cleaned += len(ids4)

    db.commit()
    if not details:
        details.append("无僵尸任务")
    return total_cleaned, details

def _recover_agent_tasks(db, agent_id: str) -> int:
    """回收 Agent 的任务"""
    now = datetime.now().isoformat()
    result = db.execute(text("""
        SELECT COUNT(*) FROM tasks
        WHERE assigned_agent = :aid AND status IN ('in_progress', 'verifying')
    """), {"aid": agent_id}).fetchone()
    count = result[0] if result else 0
    db.execute(text("""
        UPDATE tasks SET status = 'todo', assigned_agent = NULL, updated_at = :now
        WHERE assigned_agent = :aid AND status IN ('in_progress', 'verifying')
    """), {"aid": agent_id, "now": now})
    return count

def _log_heartbeat(db, agent_id: str, status: str) -> None:
    """写入心跳日志"""
    try:
        now = datetime.now().isoformat()
        db.execute(text("""
            INSERT INTO heartbeat_logs (id, agent_id, timestamp, status, latency_ms, load, current_tasks)
            VALUES (:hid, :aid, :now, :status, 0, 0, 0)
        """), {"hid": f"admin-{agent_id}-{now}", "aid": agent_id, "now": now, "status": status})
    except Exception:
        pass

def _format_agent_info(row) -> Dict[str, Any]:
    """格式化 Agent 信息"""
    caps = {}
    try:
        caps = json.loads(row.capability_tags) if row.capability_tags else {}
    except Exception:
        caps = {}
    return {
        "id": row.id, "name": row.name, "status": row.status, "capability_tags": caps,
        "address": row.address, "last_heartbeat": _to_iso(row.last_heartbeat),
        "registered_at": _to_iso(row.registered_at), "model_name": row.model_name or "",
        "task_count": row.task_count or 0
    }

def _format_task_info(row) -> Dict[str, Any]:
    """格式化任务信息"""
    return {
        "id": row.id, "title": row.title or "", "status": row.status or "unknown",
        "assigned_agent": row.assigned_agent, "priority": row.priority or 0,
        "updated_at": _to_iso(row.updated_at), "created_at": _to_iso(row.created_at),
    }