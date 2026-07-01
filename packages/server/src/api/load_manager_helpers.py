"""负载管理 API - 辅助函数与离线处理"""

import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from models.agent import Agent
from models.task import Task

def get_agent_load_info(agent_id: str, db: Session) -> Optional[dict]:
    """获取 Agent 的负载信息"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        return None
    return {
        "id": agent.id,
        "name": agent.name,
        "capabilities": agent.capability_tags,
        "status": agent.status,
        "address": agent.address,
        "metadata": agent.meta_data,
        "load": agent.load,
        "current_tasks": agent.current_tasks,
        "max_concurrent_tasks": agent.max_concurrent_tasks,
        "load_threshold": agent.load_threshold,
        "recovery_threshold": agent.recovery_threshold,
        "trigger_mode": agent.trigger_mode,
        "poll_interval_seconds": agent.poll_interval_seconds,
        "last_heartbeat": agent.last_heartbeat,
        "registered_at": agent.registered_at,
    }

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
    return db.query(func.count(Task.id)).filter(
        Task.status.in_(["todo", "pending"]),
        (Task.assigned_agent == None) | (Task.assigned_agent == agent_id)
    ).scalar() or 0

# ========== 离线处理函数 ==========

def check_and_mark_agents_offline(db: Session) -> list:
    """检查并标记超过 5 分钟未 heartbeat 的 Agent 为 offline"""
    overdue_threshold = datetime.utcnow() - timedelta(minutes=5)
    overdue_agents = db.query(Agent).filter(
        Agent.status == "online",
        Agent.last_heartbeat < overdue_threshold
    ).all()
    if not overdue_agents:
        return []
    agent_ids = [row.id for row in overdue_agents]
    now = datetime.utcnow()
    db.query(Agent).filter(Agent.id.in_(agent_ids)).update(
        {"status": "offline", "updated_at": now}, synchronize_session=False
    )
    db.commit()
    return agent_ids

def reassign_tasks_for_offline_agent(agent_id: str, db: Session):
    """为 offline Agent 重新分配任务"""
    now = datetime.utcnow()
    # Unassign pending/todo tasks
    db.query(Task).filter(
        Task.status.in_(["todo", "pending"]),
        Task.assigned_agent == agent_id
    ).update({"assigned_agent": None, "updated_at": int(now.timestamp())}, synchronize_session=False)
    # Block in_progress tasks
    db.query(Task).filter(
        Task.status == "in_progress",
        Task.assigned_agent == agent_id
    ).update({
        "status": "blocked",
        "blocked_reason": "Agent went offline",
        "updated_at": int(now.timestamp())
    }, synchronize_session=False)
    db.commit()

def reassign_all_offline_agent_tasks(db: Session):
    """为所有 offline Agent 重新分配任务"""
    offline_agents = db.query(Agent.id).filter(Agent.status == "offline").all()
    for agent_row in offline_agents:
        reassign_tasks_for_offline_agent(agent_row.id, db)
