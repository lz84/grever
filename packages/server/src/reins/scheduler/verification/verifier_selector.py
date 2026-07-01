"""
验证者选择器 — 按 domain_tags 交集排序选择验证者

职责：
1. 从 agents 表筛选 domain_tags 与 task 的 capability_tags 有交集的 agent
2. 排除 executor（不能自己审自己）
3. 按 domain 交集大小 + 验证通过率排序
4. 按需启动离线 agent
5. 无匹配 → 回退到 task.project.goal verifier
"""

import json
import asyncio
from typing import Optional, List, Dict, Any

from loguru import logger

from models import Task, Agent
from reins.common.database import get_db_manager


# ---------------------------------------------------------------------------
# Domain tag intersection scoring
# ---------------------------------------------------------------------------

def _get_agent_domain_tags(agent: Agent) -> List[str]:
    """从 agent.capability_tags 提取 domain tag 列表"""
    raw = agent.capability_tags
    if not raw:
        return []
    try:
        tags_obj = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return []
    
    # capability_tags 格式: {business:[], professional:[], technical:[], management:[]}
    # domain tags = 所有 category 下的 tags 展平
    domain_tags: List[str] = []
    for category, tags in tags_obj.items():
        if isinstance(tags, list):
            domain_tags.extend(tags)
    return domain_tags


def _get_task_domain_tags(task: Task) -> List[str]:
    """从 task.capability_tags 提取 domain tag 列表"""
    raw = task.capability_tags
    if not raw:
        return []
    try:
        tags_obj = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return []
    
    domain_tags: List[str] = []
    for category, tags in tags_obj.items():
        if isinstance(tags, list):
            domain_tags.extend(tags)
    return domain_tags


def _compute_intersection_score(task_tags: List[str], agent_tags: List[str]) -> int:
    """计算 domain tag 交集数量"""
    if not task_tags or not agent_tags:
        return 0
    task_set = set(task_tags)
    agent_set = set(agent_tags)
    return len(task_set & agent_set)


def _get_agent_verification_rate(db, agent_id: str) -> float:
    """查询 agent 的历史验证通过率（0.0 ~ 1.0）"""
    # verification_task_log 表记录验证历史
    # 通过率 = passed / total
    session = db.get_session()
    try:
        from models.verification_task_log import VerificationTaskLog
        total = session.query(VerificationTaskLog)\
            .filter(VerificationTaskLog.agent_id == agent_id)\
            .count()
        if total == 0:
            return 0.5  # 无历史，默认 0.5
        
        passed = session.query(VerificationTaskLog)\
            .filter(VerificationTaskLog.agent_id == agent_id)\
            .filter(VerificationTaskLog.passed == True)\
            .count()
        return passed / total
    except Exception:
        return 0.5
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Agent startup via OpenClaw CLI
# ---------------------------------------------------------------------------

def _start_agent_via_openclaw(agent_id: str) -> bool:
    """通过 OpenClaw CLI 启动离线 agent"""
    import subprocess
    try:
        result = subprocess.run(
            ["openclaw", "agent", "start", agent_id],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info(f"[VerifierSelector] Agent {agent_id} started successfully")
            return True
        else:
            logger.warning(f"[VerifierSelector] Failed to start agent {agent_id}: {result.stderr}")
            return False
    except FileNotFoundError:
        logger.error("[VerifierSelector] openclaw CLI not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        logger.error(f"[VerifierSelector] Timeout starting agent {agent_id}")
        return False
    except Exception as e:
        logger.error(f"[VerifierSelector] Error starting agent {agent_id}: {e}")
        return False


# ---------------------------------------------------------------------------
# Main selection logic
# ---------------------------------------------------------------------------

def select_verifier(task: Task, executor_id: str) -> Optional[str]:
    """
    选择验证者：按 domain_tags 交集排序，按需启动
    
    流程：
    1. 从 agents 表筛选 online/offline 但可启动的 agent
       - domain_tags 与 task.capability_tags 有交集
       - status != executor_id（不能自己审自己）
    2. 排序：
       - primary: domain 交集数量降序
       - secondary: 验证通过率降序
    3. 选中后，如果 agent 不在线，尝试启动
    4. 无匹配 → 回退到 task.verifier_agent_id 或 project.goal verifier
    
    Args:
        task: 任务对象
        executor_id: 执行者 agent ID（需排除）
    
    Returns:
        选中的验证者 agent_id，或 None（需人工审核）
    """
    db = get_db_manager()
    session = db.get_session()
    
    try:
        # Step 1: 获取 task 的 domain tags
        task_domain_tags = _get_task_domain_tags(task)
        
        # Step 2: 查询所有 agents（排除 executor）
        agents = session.query(Agent).filter(Agent.id != executor_id).all()
        
        if not agents:
            logger.warning(f"[VerifierSelector] No agents found (excluding {executor_id})")
            return _fallback_verifier(task, db)
        
        # Step 3: 计算每个 agent 的得分
        scored_agents: List[Dict[str, Any]] = []
        for agent in agents:
            agent_domain_tags = _get_agent_domain_tags(agent)
            intersection_count = _compute_intersection_score(task_domain_tags, agent_domain_tags)
            
            if intersection_count == 0:
                # 无交集不选中（除非没有其他选择）
                continue
            
            verification_rate = _get_agent_verification_rate(db, agent.id)
            
            scored_agents.append({
                "agent_id": agent.id,
                "agent_name": agent.name,
                "intersection_count": intersection_count,
                "verification_rate": verification_rate,
                "agent": agent,
            })
        
        if not scored_agents:
            logger.warning("[VerifierSelector] No agents with domain intersection found")
            return _fallback_verifier(task, db)
        
        # Step 4: 排序（primary: 交集数量, secondary: 通过率）
        scored_agents.sort(
            key=lambda x: (x["intersection_count"], x["verification_rate"]),
            reverse=True,
        )
        
        best = scored_agents[0]
        selected_agent = best["agent"]
        
        logger.info(
            f"[VerifierSelector] Selected {selected_agent.id} ({selected_agent.name}) "
            f"intersection={best['intersection_count']}, rate={best['verification_rate']:.2f}"
        )
        
        # Step 5: 如果 agent 不在线，尝试启动
        if selected_agent.health_status not in ("online", "active"):
            logger.info(f"[VerifierSelector] Agent {selected_agent.id} is offline, attempting to start")
            started = _start_agent_via_openclaw(selected_agent.id)
            if not started:
                # 启动失败，尝试下一个候选
                if len(scored_agents) > 1:
                    logger.warning(f"[VerifierSelector] Falling back to next candidate")
                    next_best = scored_agents[1]
                    return next_best["agent_id"]
                else:
                    return _fallback_verifier(task, db)
        
        return selected_agent.id
        
    except Exception as e:
        logger.error(f"[VerifierSelector] Error selecting verifier: {e}")
        return _fallback_verifier(task, db)
    finally:
        session.close()


def _fallback_verifier(task: Task, db) -> Optional[str]:
    """回退验证者：task.verifier_agent_id → project.verifier → goal.verifier → None"""
    session = db.get_session()
    try:
        from models.project import Project
        from models.goal import Goal
        
        # 1. task 级别
        if task.verifier_agent_id:
            return task.verifier_agent_id
        
        # 2. project 级别
        if task.project_id:
            project = session.query(Project).filter(Project.id == task.project_id).first()
            if project and project.verifier_agent_id:
                return project.verifier_agent_id
        
        # 3. goal 级别
        if task.goal_id:
            goal = session.query(Goal).filter(Goal.id == task.goal_id).first()
            if goal and goal.verifier_agent_id:
                return goal.verifier_agent_id
        
        return None
    finally:
        session.close()


def select_verifier_for_task_id(task_id: str, executor_id: str) -> Optional[str]:
    """
    select_verifier 的 ID 版本（从 task_id 获取 task 对象）
    """
    db = get_db_manager()
    session = db.get_session()
    try:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"[VerifierSelector] Task {task_id} not found")
            return None
        return select_verifier(task, executor_id)
    finally:
        session.close()
