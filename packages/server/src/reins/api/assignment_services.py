"""任务分配逻辑 (MAK-214: Agent 派发机制)

实现任务分配策略：
1. 能力匹配：任务需要的能力 ⊆ Agent 能力集
2. 负载均衡：选择当前负载最低的合格 Agent
3. 优先级排序：高优先级任务优先分配
"""

from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text
from typing import List, Optional
from datetime import datetime
import requests
import time as time_module
from loguru import logger
from vigil.common.sanitize import sanitize_execution_log

def _derive_verifier_from_goal(db: Session, goal_id: str) -> Optional[str]:
    """
    从目标继承验证者（三级继承链：Task → Project → Goal）。
    如果 Goal 有 verifier_agent_id，返回它。
    """
    if not goal_id:
        return None
    row = db.execute(sa_text("""
        SELECT verifier_agent_id FROM goals WHERE id = :gid
    """), {"gid": goal_id}).fetchone()
    return row.verifier_agent_id if row else None

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
    """计算 Agent 的负载分数（用于负载均衡）"""
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
    config_query = sa_text("""
        SELECT max_concurrent_tasks, load_threshold, recovery_threshold
        FROM agents WHERE id = :agent_id
    """)
    config_row = db.execute(config_query, {"agent_id": agent_id}).fetchone()
    max_concurrent_tasks = config_row.max_concurrent_tasks if config_row else 5
    load_threshold = config_row.load_threshold if config_row else 80

    load_limit_warning = False
    if check_load_limit:
        if agent_current_tasks >= max_concurrent_tasks or agent_load >= load_threshold:
            load_limit_warning = True

    pending_tasks_query = sa_text("""
        SELECT t.id, t.title, t.description, p.goal_id, t.priority,
               t.assigned_agent, t.status, t.dependencies, t.created_at, t.updated_at,
               t.capability_tags, t.needs_verification, t.verifier_agent_id
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
        WHERE t.status IN ('todo', 'pending', 'review_needed')
          AND (t.assigned_agent IS NULL OR t.assigned_agent = :agent_id)
        ORDER BY
            CASE t.priority
                WHEN 'critical' THEN 0
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            t.created_at ASC
    """)

    pending_tasks = db.execute(pending_tasks_query, {"agent_id": agent_id}).fetchall()
    logger.info(f"[ASSIGN-DEBUG] agent={agent_id} pending_tasks={len(pending_tasks)} "
                f"current_tasks={agent_current_tasks} load={agent_load}")

    matched_tasks = []
    for task in pending_tasks:
        task_dict = {
            "id": str(task.id) if task.id else None,
            "title": task.title,
            "description": task.description,
            "goal_id": str(task.goal_id) if task.goal_id else None,
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
    task_query = sa_text("""
        SELECT t.id, t.title, t.description, p.goal_id, t.priority,
               t.assigned_agent, t.status, t.dependencies, t.depends_on,
               t.acceptance_criteria, t.delivery_criteria, t.context_md,
               g.title as goal_title, g.description as goal_description,
               g.context_md as goal_context_md
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
        LEFT JOIN goals g ON p.goal_id = g.id
        WHERE t.id = :task_id
    """)
    task_row = db.execute(task_query, {"task_id": task_id}).fetchone()
    if not task_row:
        return {}

    task = dict(task_row._mapping) if hasattr(task_row, "_mapping") else dict(
        zip([k for k in task_row.keys()], task_row))

    scenario_query = sa_text("""
        SELECT id, name, description, scenario_desc
        FROM scenarios WHERE category = 'general'
        ORDER BY usage_count DESC LIMIT 1
    """)
    scenario_row = db.execute(scenario_query).fetchone()
    scenario_guide = None
    if scenario_row:
        steps_query = sa_text("""
            SELECT "order", name, agent_type, required_capabilities
            FROM scenario_steps WHERE scenario_id = :scenario_id
            ORDER BY "order" ASC
        """)
        steps = [{"order": s.order, "name": s.name, "agent_type": s.agent_type,
                  "required_capabilities": s.required_capabilities}
                 for s in db.execute(steps_query, {"scenario_id": scenario_row.id})]
        scenario_guide = {
            "id": scenario_row.id, "name": scenario_row.name,
            "description": scenario_row.description, "scenario_desc": scenario_row.scenario_desc,
            "steps": steps,
        }

    related_files = ["src/common/handlers.py", "src/common/utils.py"]

    history_query = sa_text("""
        SELECT id, title, status, result, completed_at
        FROM tasks WHERE status = 'done' AND id != :task_id
        ORDER BY completed_at DESC LIMIT 3
    """)
    history_rows = db.execute(history_query, {"task_id": task_id}).fetchall()
    previous_attempts = []
    for row in history_rows:
        previous_attempts.append({
            "task_id": str(row.id) if row.id else None,
            "title": row.title,
            "status": row.status,
            "result": row.result,
            "completed_at": row.completed_at.isoformat() if hasattr(row.completed_at, "isoformat") else (
                row.completed_at if row.completed_at else None),
        })

    last_verification_comment = None
    if task.get("status") == "review_needed":
        vc_query = sa_text("""
            SELECT content FROM task_comments
            WHERE task_id = :task_id AND type = 'verification'
            ORDER BY created_at DESC LIMIT 1
        """)
        vc_row = db.execute(vc_query, {"task_id": task_id}).fetchone()
        if vc_row:
            last_verification_comment = vc_row.content

    return {
        "scenario_guide": scenario_guide,
        "related_files": related_files,
        "previous_attempts": previous_attempts,
        "goal_info": {
            "id": str(task.get("goal_id")) if task.get("goal_id") else None,
            "title": task.get("goal_title"),
            "description": task.get("goal_description"),
            "context_md": task.get("goal_context_md"),
        },
        "last_verification_comment": last_verification_comment,
        # Sprint 86: 交付标准和验收标准
        "delivery_criteria": task.get("delivery_criteria"),
        "acceptance_criteria": task.get("acceptance_criteria"),
        "context_md": task.get("context_md"),
    }