"""
负载计算器（统一负载计算，2026-05-19 重构）

所有 Agent 负载必须通过 calc_dynamic_load() 动态计算，
不再依赖 DB 中可能过时的 load/current_tasks 字段。

功能：
- calc_dynamic_load()：动态查询 DB 计算真实负载（唯一入口）
- calculate_agent_load()：纯函数，给定任务数和上限算百分比
- update_agent_load() / on_heartbeat() 等：更新 DB 缓存值
"""

from loguru import logger
from typing import Tuple, Optional

# ── 纯计算函数 ─────────────────────────────────────────────

def calculate_agent_load(current_tasks: int, max_concurrent_tasks: int) -> int:
    """
    计算 Agent 负载百分比
    
    公式：load = min(100, current_tasks / max_concurrent_tasks * 100)
    
    Args:
        current_tasks: 当前任务数
        max_concurrent_tasks: 最大并发任务数
        
    Returns:
        负载百分比 (0-100)
    """
    if max_concurrent_tasks <= 0:
        return 0
    
    load = int(current_tasks / max_concurrent_tasks * 100)
    return min(100, load)

# ── 动态查询函数（2026-05-19 新增，统一入口）─────────────────

def calc_dynamic_load(conn, agent_id: str) -> Tuple[int, int]:
    """
    动态计算 Agent 真实负载（查 DB 统计待处理任务数）。
    
    这是所有 API 返回负载的统一入口，不再使用 DB 中
    可能过时的 load/current_tasks 缓存字段。
    
    Args:
        conn: SQLAlchemy connection
        agent_id: Agent ID
        
    Returns:
        (load_percent, pending_task_count)
    """
    from sqlalchemy import text
    
    row = conn.execute(text("""
        SELECT max_concurrent_tasks, COALESCE(current_tasks, 0) AS cached_tasks
        FROM agents WHERE id = :aid
    """), {"aid": agent_id}).fetchone()
    
    if not row:
        return (0, 0)
    
    max_tasks = row.max_concurrent_tasks or 5
    
    # 动态统计进行中任务（只算 in_progress）
    count = conn.execute(text("""
        SELECT COUNT(*) FROM tasks
        WHERE assigned_agent = :aid
          AND status = 'in_progress'
    """), {"aid": agent_id}).scalar() or 0
    
    load = calculate_agent_load(count, max_tasks)
    return (load, count)

def calc_all_agents_load(conn) -> dict:
    """
    一次性计算所有 Agent 的动态负载（避免 N+1 查询）。
    
    Returns:
        {agent_id: (load_percent, pending_count), ...}
    """
    from sqlalchemy import text
    
    # 获取所有 agent 的 max_concurrent_tasks
    agents = conn.execute(text("""
        SELECT id, max_concurrent_tasks FROM agents
    """)).fetchall()
    
    agent_map = {}
    for a in agents:
        max_tasks = a.max_concurrent_tasks or 5
        agent_map[a.id] = {"max": max_tasks, "count": 0}
    
    # 一次性统计所有 agent 的进行中任务（只算 in_progress）
    rows = conn.execute(text("""
        SELECT assigned_agent, COUNT(*) AS cnt
        FROM tasks
        WHERE assigned_agent IS NOT NULL
          AND status = 'in_progress'
        GROUP BY assigned_agent
    """)).fetchall()
    
    for r in rows:
        if r.assigned_agent in agent_map:
            agent_map[r.assigned_agent]["count"] = r.cnt
    
    result = {}
    for aid, info in agent_map.items():
        load = calculate_agent_load(info["count"], info["max"])
        result[aid] = (load, info["count"])
    
    return result

def calculate_agent_load(current_tasks: int, max_concurrent_tasks: int) -> int:
    """
    计算 Agent 负载百分比
    
    公式：load = min(100, current_tasks / max_concurrent_tasks * 100)
    
    Args:
        current_tasks: 当前任务数
        max_concurrent_tasks: 最大并发任务数
        
    Returns:
        负载百分比 (0-100)
    """
    if max_concurrent_tasks <= 0:
        return 0
    
    load = int(current_tasks / max_concurrent_tasks * 100)
    return min(100, load)

def update_agent_load(db, agent_id: str, current_tasks: int = None) -> Tuple[int, int]:
    """
    更新 Agent 负载
    
    逻辑：
    1. 如果提供了 current_tasks，先更新 current_tasks
    2. 重新计算 load
    3. 更新数据库
    
    Args:
        db: 数据库连接
        agent_id: Agent ID
        current_tasks: 新的任务数（可选）
        
    Returns:
        (新的 load, current_tasks)
    """
    try:
        from sqlalchemy import text
        from datetime import datetime
        
        # 先查询当前值
        agent_row = db.execute(text("""
            SELECT current_tasks, max_concurrent_tasks
            FROM agents
            WHERE id = :agent_id
        """), {"agent_id": agent_id}).fetchone()
        
        if not agent_row:
            logger.warning(f"[LoadCalculator] Agent {agent_id} not found")
            return (0, 0)
        
        # 如果提供了新的 current_tasks，使用它；否则使用数据库中的值
        new_current_tasks = current_tasks if current_tasks is not None else agent_row.current_tasks
        max_concurrent_tasks = agent_row.max_concurrent_tasks
        
        # 计算新负载
        new_load = calculate_agent_load(new_current_tasks, max_concurrent_tasks)
        
        # 更新数据库
        db.execute(text("""
            UPDATE agents
            SET load = :load,
                current_tasks = :current_tasks,
                updated_at = :now
            WHERE id = :agent_id
        """), {
            "agent_id": agent_id,
            "load": new_load,
            "current_tasks": new_current_tasks,
            "now": datetime.now()
        })
        
        logger.info(f"[LoadCalculator] Agent {agent_id}: load={new_load}%, current_tasks={new_current_tasks}, max_concurrent_tasks={max_concurrent_tasks}")
        
        return (new_load, new_current_tasks)
        
    except Exception as e:
        logger.error(f"[LoadCalculator] Failed to update load for agent {agent_id}: {e}")
        return (0, 0)

def on_heartbeat(db, agent_id: str, current_tasks: int = None) -> dict:
    """
    Agent 心跳时的负载更新
    
    Args:
        db: 数据库连接
        agent_id: Agent ID
        current_tasks: 心跳中报告的任务数（可选）
        
    Returns:
        更新后的负载信息
    """
    new_load, new_current_tasks = update_agent_load(db, agent_id, current_tasks)
    return {
        "agent_id": agent_id,
        "load": new_load,
        "current_tasks": new_current_tasks,
        "timestamp": datetime.now().isoformat() if 'datetime' in dir() else None
    }

def on_task_assigned(db, agent_id: str) -> dict:
    """
    任务分配给 Agent 后的负载更新
    
    Args:
        db: 数据库连接
        agent_id: Agent ID
        
    Returns:
        更新后的负载信息
    """
    # increment current_tasks and recalculate load
    from sqlalchemy import text
    from datetime import datetime
    
    try:
        # 增加 current_tasks
        result = db.execute(text("""
            UPDATE agents
            SET current_tasks = current_tasks + 1,
                updated_at = :now
            WHERE id = :agent_id
            RETURNING current_tasks, max_concurrent_tasks
        """), {"agent_id": agent_id, "now": datetime.now()}).fetchone()
        
        if not result:
            logger.warning(f"[LoadCalculator] Agent {agent_id} not found when incrementing tasks")
            return {"error": "agent_not_found"}
        
        new_current_tasks = result.current_tasks
        max_concurrent_tasks = result.max_concurrent_tasks
        new_load = calculate_agent_load(new_current_tasks, max_concurrent_tasks)
        
        # 更新 load 字段
        db.execute(text("""
            UPDATE agents
            SET load = :load,
                updated_at = :now
            WHERE id = :agent_id
        """), {
            "agent_id": agent_id,
            "load": new_load,
            "now": datetime.now()
        })
        
        logger.info(f"[LoadCalculator] Task assigned to {agent_id}: load={new_load}%, current_tasks={new_current_tasks}")
        
        return {
            "agent_id": agent_id,
            "load": new_load,
            "current_tasks": new_current_tasks,
            "action": "task_assigned"
        }
        
    except Exception as e:
        logger.error(f"[LoadCalculator] Failed to increment load for agent {agent_id}: {e}")
        return {"error": str(e)}

def on_task_completed(db, agent_id: str) -> dict:
    """
    任务完成后的负载更新
    
    Args:
        db: 数据库连接
        agent_id: Agent ID
        
    Returns:
        更新后的负载信息
    """
    from sqlalchemy import text
    from datetime import datetime
    
    try:
        # 减少 current_tasks（不低于 0）
        result = db.execute(text("""
            UPDATE agents
            SET current_tasks = MAX(0, current_tasks - 1),
                updated_at = :now
            WHERE id = :agent_id
            RETURNING current_tasks, max_concurrent_tasks
        """), {"agent_id": agent_id, "now": datetime.now()}).fetchone()
        
        if not result:
            logger.warning(f"[LoadCalculator] Agent {agent_id} not found when decrementing tasks")
            return {"error": "agent_not_found"}
        
        new_current_tasks = result.current_tasks
        max_concurrent_tasks = result.max_concurrent_tasks
        new_load = calculate_agent_load(new_current_tasks, max_concurrent_tasks)
        
        # 更新 load 字段
        db.execute(text("""
            UPDATE agents
            SET load = :load,
                updated_at = :now
            WHERE id = :agent_id
        """), {
            "agent_id": agent_id,
            "load": new_load,
            "now": datetime.now()
        })
        
        logger.info(f"[LoadCalculator] Task completed for {agent_id}: load={new_load}%, current_tasks={new_current_tasks}")
        
        return {
            "agent_id": agent_id,
            "load": new_load,
            "current_tasks": new_current_tasks,
            "action": "task_completed"
        }
        
    except Exception as e:
        logger.error(f"[LoadCalculator] Failed to decrement load for agent {agent_id}: {e}")
        return {"error": str(e)}

def get_agent_load_info(db, agent_id: str) -> dict:
    """
    获取 Agent 的负载信息
    
    Args:
        db: 数据库连接
        agent_id: Agent ID
        
    Returns:
        负载信息字典
    """
    try:
        from sqlalchemy import text
        
        row = db.execute(text("""
            SELECT id, name, load, current_tasks, max_concurrent_tasks,
                   load_threshold, recovery_threshold, health_status, status
            FROM agents
            WHERE id = :agent_id
        """), {"agent_id": agent_id}).fetchone()
        
        if not row:
            return None
        
        # 计算理论负载
        calculated_load = calculate_agent_load(row.current_tasks, row.max_concurrent_tasks)
        
        return {
            "agent_id": row.id,
            "agent_name": row.name,
            "load": row.load if row.load is not None else calculated_load,
            "calculated_load": calculated_load,
            "current_tasks": row.current_tasks,
            "max_concurrent_tasks": row.max_concurrent_tasks,
            "load_threshold": row.load_threshold,
            "recovery_threshold": row.recovery_threshold,
            "health_status": row.health_status,
            "status": row.status,
            "is_overloaded": calculated_load >= row.load_threshold if row.load_threshold else False
        }
        
    except Exception as e:
        logger.error(f"[LoadCalculator] Failed to get load info for agent {agent_id}: {e}")
        return None
