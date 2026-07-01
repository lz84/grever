"""
Task Assigner 辅助函数（从 task_assigner.py 拆分）

包含：
- _assign_agent: 选择负载最低的在线 Agent
- _assign_agent_excluding: 选择排除指定 ID 的在线 Agent
- _assign_by_capability: 用匹配引擎 + fallback 选择 Agent
- _assign_verifier: 选择验证者 Agent
"""
from loguru import logger
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models.agent import Agent
from models.task import Task


def _assign_agent(session: Session) -> Optional[str]:
    """
    选择负载最低的在线 Agent（供任务创建时调用）

    返回：
        Agent UUID，如果没有在线 agent 返回 None
    """
    try:
        # 实时从 tasks 表算 in_progress 任务数，不再依赖 current_tasks 列（会漂移）
        # 子查询：统计该 Agent 当前的 in_progress/running 任务数
        in_progress_subq = (
            select(func.count(Task.id))
            .where(Task.assigned_agent == Agent.id)
            .where(Task.status.in_(['in_progress', 'running']))
            .scalar_subquery()
        )

        result = (
            session.query(Agent.id)
            .filter(Agent.health_status == 'online')
            .filter(in_progress_subq < Agent.max_concurrent_tasks)
            .order_by(
                (in_progress_subq * 10 + func.coalesce(Agent.load, 0)).asc()
            )
            .limit(1)
            .first()
        )
        if result:
            return result.id

        # 兜底：即使满载也选一个在线的（防止死锁，但不应该走到这里）
        result = (
            session.query(Agent.id)
            .filter(Agent.health_status == 'online')
            .order_by(func.coalesce(Agent.load, 0).asc())
            .limit(1)
            .first()
        )
        if result:
            return result.id
        return None
    except Exception as e:
        logger.error(f"[TaskAssigner] _assign_agent error: {e}")
        return None


def _assign_agent_excluding(session: Session, exclude_id: str) -> Optional[str]:
    """选择负载最低的在线 Agent，排除指定 ID"""
    try:
        # 实时从 tasks 表算 in_progress 任务数
        in_progress_subq = (
            select(func.count(Task.id))
            .where(Task.assigned_agent == Agent.id)
            .where(Task.status.in_(['in_progress', 'running']))
            .scalar_subquery()
        )

        result = (
            session.query(Agent.id)
            .filter(Agent.health_status == 'online')
            .filter(Agent.id != exclude_id)
            .filter(in_progress_subq < Agent.max_concurrent_tasks)
            .order_by(
                (in_progress_subq * 10 + func.coalesce(Agent.load, 0)).asc()
            )
            .limit(1)
            .first()
        )
        if result:
            return result.id

        # 兜底：即使满载也选一个不同的在线 Agent
        result = (
            session.query(Agent.id)
            .filter(Agent.health_status == 'online')
            .filter(Agent.id != exclude_id)
            .order_by(
                (in_progress_subq * 10 + func.coalesce(Agent.load, 0)).asc()
            )
            .limit(1)
            .first()
        )
        if result:
            return result.id
        return None
    except Exception as e:
        logger.error(f"[TaskAssigner] _assign_agent_excluding error: {e}")
        return None


def _assign_by_capability(session: Session, capability_tags: dict) -> Optional[str]:
    """
    用匹配引擎选择 Agent，fallback 到负载选择。

    参数：
        session: 数据库会话
        capability_tags: 任务的多维能力标签字典 (如 {"technical": ["python", "ml"]})

    返回：
        Agent UUID，如果没有匹配的在线 agent 则 fallback 到负载选择
    """
    if not capability_tags:
        return _assign_agent(session)  # fallback 到负载选择

    try:
        from reins.scheduler.assigner.agent_matcher import match_for_task
        results = match_for_task(capability_tags)
        if results:
            return results[0]["agent_id"]  # 选最高分的 Agent
    except Exception as e:
        logger.warning(f"[TaskAssigner] _assign_by_capability match failed: {e}")

    # 匹配失败或无结果 → fallback 到负载选择
    return _assign_agent(session)


def _assign_verifier(session: Session, executor_id: str, capability_tags: dict = None) -> Optional[str]:
    """
    选择验证者：有能力验证此任务 且不是执行者的在线 Agent

    逻辑：
    1. 优先用匹配引擎找有相关能力的 Agent（排除执行者）
    2. fallback 到负载最低的在线不同 Agent

    参数：
        session: 数据库会话
        executor_id: 执行者 Agent ID（验证者不能是同一个人）
        capability_tags: 任务的能力标签，用于匹配有能力的验证者

    返回：
        Agent UUID，如果没有可用的不同 Agent 返回 None
    """
    if not capability_tags:
        return _assign_agent_excluding(session, executor_id)

    try:
        from reins.scheduler.assigner.agent_matcher import match_for_task
        results = match_for_task(capability_tags)
        # 找第一个不是执行者的 Agent
        for r in results:
            if r["agent_id"] != executor_id:
                return r["agent_id"]
    except Exception as e:
        logger.warning(f"[TaskAssigner] _assign_verifier match failed: {e}")

    # 匹配失败 → fallback 到负载选择（排除执行者）
    return _assign_agent_excluding(session, executor_id)
