"""任务分配逻辑 (MAK-214: Agent 派发机制)

实现任务分配策略:
1. 能力匹配:任务需要的能力 ⊆ Agent 能力集
2. 负载均衡:选择当前负载最低的合格 Agent
3. 优先级排序:高优先级任务优先分配
"""

import json
from sqlalchemy.orm import Session
from sqlalchemy import case
from typing import List, Optional
from datetime import datetime
import requests
import time as time_module
from loguru import logger

from models.goal import Goal
from models.project import Project
from models.task import Task
from models.agent import Agent
from models.scenario import Scenario, ScenarioTask
from models.task_comment import TaskComment


def _derive_verifier_from_goal(db: Session, goal_id: str) -> Optional[str]:
    """
    从目标继承验证者(三级继承链:Task → Project → Goal)。
    如果 Goal 有 verifier_agent_id,返回它。
    """
    if not goal_id:
        return None
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    return goal.verifier_agent_id if goal else None

# ========== 模型连通性检查 ==========

def check_model_connectivity(address: str, timeout: float = 3.0) -> tuple[bool, int, str]:
    """检查 agent model endpoint 的连通性"""
    if not address:
        return False, 0, "No address provided"

    base_url = address.rstrip("/")
    endpoints = ["/health", "/api/status"]
    start_time = time_module.time()

    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, timeout=timeout)
            duration_ms = int((time_module.time() - start_time) * 1000)
            if response.status_code < 500:
                return True, duration_ms, ""
        except requests.exceptions.Timeout:
            duration_ms = int((time_module.time() - start_time) * 1000)
            return False, duration_ms, f"Connection timeout ({timeout}s) to {endpoint}"
        except requests.exceptions.ConnectionError:
            duration_ms = int((time_module.time() - start_time) * 1000)
            continue
        except Exception as e:
            duration_ms = int((time_module.time() - start_time) * 1000)
            return False, duration_ms, str(e)

    duration_ms = int((time_module.time() - start_time) * 1000)
    return False, duration_ms, f"Could not connect to any endpoint ({', '.join(endpoints)})"

# ========== 任务分配逻辑 ==========

def matches_capabilities(task: dict, agent: dict) -> bool:
    """检查任务是否与 Agent 能力匹配"""
    if not task.get("required_capabilities"):
        return True

    agent_capabilities = set(agent.get("capabilities", []))
    task_capabilities = set(task.get("required_capabilities", []))
    return task_capabilities.issubset(agent_capabilities)

def get_load_score(agent: dict) -> int:
    """计算 Agent 的负载分数(用于负载均衡)"""
    current_tasks = agent.get("current_tasks", 0)
    load = agent.get("load", 0)
    return current_tasks * 10 + load

def assign_tasks_to_agent(
    agent_id: str,
    agent_capabilities: List[str],
    agent_current_tasks: int,
    agent_load: int,
    db: Session,
    check_load_limit: bool = True
) -> tuple[List[dict], bool]:
    """分配 pending 任务给指定 agent"""
    # 查 Agent 配置
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    max_concurrent_tasks = agent.max_concurrent_tasks if agent else 5
    load_threshold = agent.load_threshold if agent else 80

    load_limit_warning = False
    if check_load_limit:
        if agent_current_tasks >= max_concurrent_tasks or agent_load >= load_threshold:
            load_limit_warning = True

    # ORM 查 pending tasks（按优先级排序，用 case 表达式）
    priority_order = case(
        (Task.priority == 'critical', 0),
        (Task.priority == 'high', 1),
        (Task.priority == 'medium', 2),
        (Task.priority == 'low', 3),
        else_=4,
    )
    pending_tasks = db.query(Task).filter(
        Task.status.in_(['todo', 'pending', 'review_needed']),
        (Task.assigned_agent == None) | (Task.assigned_agent == agent_id)
    ).order_by(priority_order, Task.created_at.asc()).all()

    logger.info(f"[ASSIGN-DEBUG] agent={agent_id} pending_tasks={len(pending_tasks)} "
                f"current_tasks={agent_current_tasks} load={agent_load}")

    # 构建 project_id → goal_id 映射（批量查询，避免 N+1）
    project_ids = list({t.project_id for t in pending_tasks if t.project_id})
    goal_map = {}
    if project_ids:
        projects = db.query(Project).filter(Project.id.in_(project_ids)).all()
        goal_map = {p.id: p.goal_id for p in projects}

    matched_tasks = []
    for task in pending_tasks:
        goal_id = goal_map.get(task.project_id) if task.project_id else getattr(task, 'goal_id', None)
        task_dict = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "goal_id": str(goal_id) if goal_id else None,
            "priority": task.priority,
            "category": None,
            "assigned_agent": task.assigned_agent,
            "status": task.status,
            "dependencies": task.dependencies,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "required_capabilities": None,
            "capability_tags": task.capability_tags,
            "needs_verification": task.needs_verification,
            "verifier_agent_id": task.verifier_agent_id,
        }
        if matches_capabilities(task_dict, {"capabilities": agent_capabilities}):
            matched_tasks.append(task_dict)

    if load_limit_warning:
        return [], True

    available_slots = max_concurrent_tasks - agent_current_tasks
    assigned_tasks = []
    for task in matched_tasks:
        if len(assigned_tasks) >= max_concurrent_tasks:
            break
        if len(assigned_tasks) >= available_slots:
            load_limit_warning = True
            break
        task_context = get_task_context(task["id"], db)

        # 同时分配验证者（needs_verification=True 且尚无 verifier 时）
        final_verifier_id = task["verifier_agent_id"]
        if task["needs_verification"] and not final_verifier_id:
            # 从目标继承 verifier
            final_verifier_id = _derive_verifier_from_goal(db, task["goal_id"])
            if final_verifier_id:
                logger.info(f"[assign_tasks_to_agent] Assigned verifier {final_verifier_id} for task {task['id']}")

        assigned_tasks.append({
            "id": task["id"],
            "title": task["title"],
            "description": task["description"],
            "goal_id": task["goal_id"],
            "priority": task["priority"],
            "context": task_context,
            "assigned_agent": agent_id,
            "verifier_agent_id": final_verifier_id,
        })

    return assigned_tasks, load_limit_warning

def get_task_context(task_id: str, db: Session) -> dict:
    """获取任务上下文信息"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return {}

    # 通过 project 获取 goal_id
    goal_id = None
    goal_title = None
    goal_description = None
    goal_context_md = None
    if task.project_id:
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if project:
            goal_id = project.goal_id
            if project.goal_id:
                goal = db.query(Goal).filter(Goal.id == project.goal_id).first()
                if goal:
                    goal_title = goal.title
                    goal_description = goal.description
                    goal_context_md = goal.context_md

    # 查询最常用场景（general 分类）
    scenario = db.query(Scenario).filter(
        Scenario.category == 'general'
    ).order_by(Scenario.usage_count.desc()).first()
    scenario_guide = None
    if scenario:
        # scenario_steps 表已删除，步骤数据在 scenario_tasks 中
        scenario_steps_raw = db.query(ScenarioTask).filter(
            ScenarioTask.scenario_id == scenario.id
        ).order_by(ScenarioTask.order_in_phase.asc()).all()
        steps = [{
            "order": s.order_in_phase,
            "name": s.name,
            "agent_type": s.agent_type,
            "required_capabilities": s.required_capabilities,
        } for s in scenario_steps_raw]
        scenario_guide = {
            "id": scenario.id,
            "name": scenario.name,
            "description": scenario.description,
            "scenario_desc": scenario.scenario_desc,
            "steps": steps,
        }

    related_files = ["src/common/handlers.py", "src/common/utils.py"]

    # 历史已完成任务（排除当前任务）
    history_tasks = db.query(Task).filter(
        Task.status == 'done',
        Task.id != task_id
    ).order_by(Task.completed_at.desc()).limit(3).all()
    previous_attempts = []
    for h in history_tasks:
        completed_at_iso = None
        if h.completed_at:
            if isinstance(h.completed_at, int):
                completed_at_iso = datetime.utcfromtimestamp(h.completed_at).isoformat()
            elif hasattr(h.completed_at, 'isoformat'):
                completed_at_iso = h.completed_at.isoformat()
        previous_attempts.append({
            "task_id": h.id,
            "title": h.title,
            "status": h.status,
            "result": h.result,
            "completed_at": completed_at_iso,
        })

    last_verification_comment = None
    if task.status == "review_needed":
        vc = db.query(TaskComment).filter(
            TaskComment.task_id == task_id,
            TaskComment.type == 'verification'
        ).order_by(TaskComment.created_at.desc()).first()
        if vc:
            last_verification_comment = vc.content

    return {
        "scenario_guide": scenario_guide,
        "related_files": related_files,
        "previous_attempts": previous_attempts,
        "goal_info": {
            "id": str(goal_id) if goal_id else None,
            "title": goal_title,
            "description": goal_description,
            "context_md": goal_context_md,
        },
        "last_verification_comment": last_verification_comment,
        "delivery_criteria": task.delivery_criteria,
        "acceptance_criteria": task.acceptance_criteria,
        "context_md": task.context_md,
    }