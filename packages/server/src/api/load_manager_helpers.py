"""负载管理 API - 辅助函数与离线处理"""

import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

def get_agent_load_info(agent_id: str, db: Session) -> Optional[dict]:
    """获取 Agent 的负载信息"""
    agent_query = text("""
        SELECT id, name, capabilities, status, address, metadata,
               load, current_tasks, max_concurrent_tasks, load_threshold, recovery_threshold,
               trigger_mode, poll_interval_seconds, last_heartbeat, registered_at
        FROM agents
        WHERE id = :agent_id
    """)
    agent_row = db.execute(agent_query, {"agent_id": agent_id}).fetchone()
    if not agent_row:
        return None
    return dict(agent_row)

def check_agent_online(agent: dict) -> bool:
    """检查 Agent 是否在线（最近 5 分钟有 heartbeat）"""
    last_heartbeat = agent.get("last_heartbeat")
    if not last_heartbeat:
        return False
    overdue_threshold = datetime.utcnow() - timedelta(minutes=5)
    if isinstance(last_heartbeat, str):
        last_heartbeat = datetime.fromisoformat(last_heartbeat)
    return last_heartbeat >= overdue_threshold

def get_pending_tasks_count(agent_id: str, db: Session) -> int:
    """获取 Agent 的待领取任务数"""
    query = text("""
        SELECT COUNT(*) as count
        FROM tasks
        WHERE status IN ('todo', 'pending')
          AND (assigned_agent IS NULL OR assigned_agent = :agent_id)
    """)
    result = db.execute(query, {"agent_id": agent_id}).fetchone()
    return result.count if result else 0

# ========== 离线处理函数 ==========

def check_and_mark_agents_offline(db: Session) -> list:
    """检查并标记超过 5 分钟未 heartbeat 的 Agent 为 offline"""
    overdue_threshold = datetime.utcnow() - timedelta(minutes=5)
    query = text("""
        SELECT id, name, status
        FROM agents
        WHERE status = 'online'
          AND last_heartbeat < :threshold
    """)
    overdue_agents = db.execute(query, {"threshold": overdue_threshold}).fetchall()
    if not overdue_agents:
        return []
    agent_ids = [row.id for row in overdue_agents]
    agent_ids_str = ",".join(f"'{id}'" for id in agent_ids)
    db.execute(text(
        f"UPDATE agents SET status = 'offline', updated_at = :now WHERE id IN ({agent_ids_str})"
    ), {"now": datetime.utcnow()})
    db.commit()
    return agent_ids

def reassign_tasks_for_offline_agent(agent_id: str, db: Session):
    """为 offline Agent 重新分配任务"""
    pending_query = text("""
        SELECT id FROM tasks
        WHERE status IN ('todo', 'pending') AND assigned_agent = :agent_id
    """)
    pending_tasks = db.execute(pending_query, {"agent_id": agent_id}).fetchall()
    if pending_tasks:
        reassign_query = text("""
            UPDATE tasks SET assigned_agent = NULL, updated_at = :now
            WHERE status IN ('todo', 'pending') AND assigned_agent = :agent_id
        """)
        db.execute(reassign_query, {"agent_id": agent_id, "now": datetime.utcnow()})
    in_progress_query = text("""
        UPDATE tasks SET status = 'blocked', blocked_reason = 'Agent went offline', updated_at = :now
        WHERE status = 'in_progress' AND assigned_agent = :agent_id
    """)
    db.execute(in_progress_query, {"agent_id": agent_id, "now": datetime.utcnow()})
    db.commit()

def reassign_all_offline_agent_tasks(db: Session):
    """为所有 offline Agent 重新分配任务"""
    query = text("SELECT id FROM agents WHERE status = 'offline'")
    offline_agents = db.execute(query).fetchall()
    for agent_row in offline_agents:
        reassign_tasks_for_offline_agent(agent_row.id, db)
