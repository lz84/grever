"""任务分配核心逻辑模块

MAK-214: Agent 派发机制 - 任务分配策略
"""

from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

def matches_capabilities(task: dict, agent: dict) -> bool:
    """
    检查任务是否与 Agent 能力匹配
    
    1. 如果任务没有指定 required_capabilities，则匹配
    2. 如果任务指定了 required_capabilities，则 Agent 必须具备所有这些能力
    """
    if not task.get("required_capabilities"):
        return True
    
    agent_capabilities = set(agent.get("capabilities", []))
    task_capabilities = set(task.get("required_capabilities", []))
    
    return task_capabilities.issubset(agent_capabilities)

def get_load_score(agent: dict) -> int:
    """
    计算 Agent 的负载分数（用于负载均衡）
    
    负载分数 = 当前任务数 * 10 + 当前负载百分比
    分数越低，负载越轻
    """
    current_tasks = agent.get("current_tasks", 0)
    load = agent.get("load", 0)
    return current_tasks * 10 + load

def get_task_context(task_id: str, db: Session) -> dict:
    """
    获取任务上下文信息
    注意：task_id 是 String 类型
    """
    # 1. 获取任务详情（goal_id 通过 project 关联）
    task_query = sa_text("""
        SELECT t.id, t.title, t.description, p.goal_id, t.priority,
               t.assigned_agent, t.status, t.dependencies, t.depends_on,
               g.title as goal_title, g.description as goal_description
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
        LEFT JOIN goals g ON p.goal_id = g.id
        WHERE t.id = :task_id
    """)
    
    task_row = db.execute(task_query, {"task_id": task_id}).fetchone()
    if not task_row:
        return {}
    
    task = dict(task_row._mapping) if hasattr(task_row, "_mapping") else dict(zip([k for k in task_row.keys()], task_row))
    
    # 2. 获取相关场景指南（使用 general 场景）
    scenario_query = sa_text("""
        SELECT id, name, description, scenario_desc
        FROM scenarios
        WHERE category = 'general'
        ORDER BY usage_count DESC
        LIMIT 1
    """)
    
    scenario_row = db.execute(scenario_query).fetchone()
    scenario_guide = None
    if scenario_row:
        steps_query = sa_text("""
            SELECT "order", name, agent_type, required_capabilities
            FROM scenario_steps
            WHERE scenario_id = :scenario_id
            ORDER BY "order" ASC
        """)
        steps = []
        for step_row in db.execute(steps_query, {"scenario_id": scenario_row.id}):
            steps.append({
                "order": step_row.order,
                "name": step_row.name,
                "agent_type": step_row.agent_type,
                "required_capabilities": step_row.required_capabilities,
            })
        
        scenario_guide = {
            "id": scenario_row.id,
            "name": scenario_row.name,
            "description": scenario_row.description,
            "scenario_desc": scenario_row.scenario_desc,
            "steps": steps,
        }
    
    # 3. 获取相关文件
    related_files = [
        "src/common/handlers.py",
        "src/common/utils.py",
    ]
    
    # 4. 获取历史执行记录
    history_query = sa_text("""
        SELECT id, title, status, result, completed_at
        FROM tasks
        WHERE status = 'done'
          AND id != :task_id
        ORDER BY completed_at DESC
        LIMIT 3
    """)
    
    history_rows = db.execute(history_query, {"task_id": task_id}).fetchall()
    
    previous_attempts = []
    for row in history_rows:
        previous_attempts.append({
            "task_id": str(row.id) if row.id else None,
            "title": row.title,
            "status": row.status,
            "result": row.result,
            "completed_at": row.completed_at.isoformat() if hasattr(row.completed_at, "isoformat") else (row.completed_at if row.completed_at else None),
        })
    
    # 5. 获取最近的 verification comment（用于 review_needed 任务的重新派发）
    last_verification_comment = None
    if task.get("status") == "review_needed":
        vc_query = sa_text("""
            SELECT content, metadata
            FROM task_comments
            WHERE task_id = :task_id AND type = 'verification'
            ORDER BY created_at DESC
            LIMIT 1
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
        },
        "last_verification_comment": last_verification_comment,
    }

def assign_tasks_to_agent(
    agent_id: str,
    agent_capabilities: List[str],
    agent_current_tasks: int,
    agent_load: int,
    db: Session,
    check_load_limit: bool = True
) -> Tuple[List[dict], bool]:
    """
    分配 pending 任务给指定 agent
    
    参数：
    - check_load_limit: 是否检查负载限制（默认 True）
    
    返回：
    - assigned_tasks: 分配的任务列表
    - load_limit_warning: 是否超过负载限制
    """
    # 1. 获取 Agent 的负载配置
    config_query = sa_text("""
        SELECT max_concurrent_tasks, load_threshold, recovery_threshold
        FROM agents
        WHERE id = :agent_id
    """)
    
    config_row = db.execute(config_query, {"agent_id": agent_id}).fetchone()
    max_concurrent_tasks = config_row.max_concurrent_tasks if config_row else 5
    load_threshold = config_row.load_threshold if config_row else 80
    
    # 检查是否超载
    load_limit_warning = False
    if check_load_limit:
        if agent_current_tasks >= max_concurrent_tasks or agent_load >= load_threshold:
            load_limit_warning = True
    
    # 2. 获取所有 pending 任务（goal_id 通过 project 关联）
    pending_tasks_query = sa_text("""
        SELECT 
            t.id, t.title, t.description, p.goal_id, t.priority,
            t.assigned_agent, t.status, t.dependencies, t.created_at, t.updated_at
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
    logger.info(f"[ASSIGN-DEBUG] agent={agent_id} pending_tasks={len(pending_tasks)} current_tasks={agent_current_tasks} load={agent_load}")
    for pt in pending_tasks[:5]:
        logger.info(f"[ASSIGN-DEBUG]   task={pt[0]} status={pt[6]} assigned={pt[5]}")
    
    # 3. 能力匹配过滤
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
        }
        
        if matches_capabilities(task_dict, {
            "capabilities": agent_capabilities
        }):
            matched_tasks.append(task_dict)
    
    # 4. 负载检查
    if load_limit_warning:
        return [], True
    
    available_slots = max_concurrent_tasks - agent_current_tasks
    
    # 5. 分配任务（限制在负载上限内）
    assigned_tasks = []
    for task in matched_tasks:
        if len(assigned_tasks) >= max_concurrent_tasks:
            break
        if len(assigned_tasks) >= available_slots:
            load_limit_warning = True
            break
        
        task_context = get_task_context(task["id"], db)
        
        assigned_tasks.append({
            "id": task["id"],
            "title": task["title"],
            "description": task["description"],
            "goal_id": task["goal_id"],
            "priority": task["priority"],
            "context": task_context,
        })
    
    return assigned_tasks, load_limit_warning