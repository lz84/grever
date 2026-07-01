"""
任务分配器

Phase 2: 实现 TaskAssigner 类
- assign_pending_tasks(): 分配待处理任务给空闲 Agent
- redistribute_recovered(): 重新分配 recovery_count > 0 的任务
"""
from loguru import logger

from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import text

from reins.scheduler.load_calculator import on_task_assigned, on_task_completed, calculate_agent_load, update_agent_load

def _assign_by_capability(db, capability_tags: dict) -> Optional[str]:
    """
    用匹配引擎选择 Agent，fallback 到负载选择。
    
    参数：
        db: 数据库连接
        capability_tags: 任务的多维能力标签字典 (如 {"technical": ["python", "ml"]})
    
    返回：
        Agent UUID，如果没有匹配的在线 agent 则 fallback 到负载选择
    """
    if not capability_tags:
        return _assign_agent(db)  # fallback 到负载选择

    try:
        from reins.scheduler.assigner.agent_matcher import match_for_task
        results = match_for_task(capability_tags)
        if results:
            return results[0]["agent_id"]  # 选最高分的 Agent
    except Exception as e:
        logger.warning(f"[TaskAssigner] _assign_by_capability match failed: {e}")

    # 匹配失败或无结果 → fallback 到负载选择
    return _assign_agent(db)

def _assign_agent(db) -> Optional[str]:
    """
    选择负载最低的在线 Agent（供任务创建时调用）
    
    返回：
        Agent UUID，如果没有在线 agent 返回 None
    """
    try:
        # 实时从 tasks 表算 in_progress 任务数，不再依赖 current_tasks 列（会漂移）
        result = db.execute(text("""
            SELECT a.id FROM agents a
            WHERE a.health_status = 'online'
              AND (
                  SELECT COUNT(*) FROM tasks t
                  WHERE t.assigned_agent = a.id
                    AND t.status IN ('in_progress', 'running')
              ) < a.max_concurrent_tasks
            ORDER BY (
                (SELECT COUNT(*) FROM tasks t2
                 WHERE t2.assigned_agent = a.id AND t2.status IN ('in_progress', 'running')
                ) * 10 + COALESCE(a.load, 0)
            ) ASC
            LIMIT 1
        """)).fetchone()
        if result:
            return result[0]
        # 兜底：即使满载也选一个在线的（防止死锁，但不应该走到这里）
        result = db.execute(text("""
            SELECT id FROM agents
            WHERE health_status = 'online'
            ORDER BY (COALESCE(load, 0)) ASC
            LIMIT 1
        """)).fetchone()
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"[TaskAssigner] _assign_agent error: {e}")
        return None

def _assign_verifier(db, executor_id: str, capability_tags: dict = None) -> Optional[str]:
    """
    选择验证者：有能力验证此任务 且不是执行者的在线 Agent
    
    逻辑：
    1. 优先用匹配引擎找有相关能力的 Agent（排除执行者）
    2. fallback 到负载最低的在线不同 Agent
    
    参数：
        db: 数据库连接
        executor_id: 执行者 Agent ID（验证者不能是同一个人）
        capability_tags: 任务的能力标签，用于匹配有能力的验证者
    
    返回：
        Agent UUID，如果没有可用的不同 Agent 返回 None
    """
    if not capability_tags:
        return _assign_agent_excluding(db, executor_id)

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
    return _assign_agent_excluding(db, executor_id)

def _assign_agent_excluding(db, exclude_id: str) -> Optional[str]:
    """选择负载最低的在线 Agent，排除指定 ID"""
    try:
        result = db.execute(text("""
            SELECT id FROM agents
            WHERE health_status = 'online'
              AND id != :exclude_id
              AND current_tasks < max_concurrent_tasks
            ORDER BY (current_tasks * 10 + COALESCE(load, 0)) ASC
            LIMIT 1
        """), {"exclude_id": exclude_id}).fetchone()
        if result:
            return result[0]
        # 兜底：即使满载也选一个不同的在线 Agent
        result = db.execute(text("""
            SELECT id FROM agents
            WHERE health_status = 'online'
              AND id != :exclude_id
            ORDER BY (current_tasks * 10 + COALESCE(load, 0)) ASC
            LIMIT 1
        """), {"exclude_id": exclude_id}).fetchone()
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"[TaskAssigner] _assign_agent_excluding error: {e}")
        return None

class TaskAssigner:
    """
    任务分配器
    
    负责将待处理任务分配给负载最低的在线 Agent
    """

    def __init__(self, db_manager):
        self.db = db_manager

    def _get_lowest_load_online_agent(self, db) -> Optional[str]:
        """获取负载最低的在线 Agent（内部使用 _assign_agent）"""
        return _assign_agent(db)

    def _get_agent_capabilities(self, db, agent_id: str) -> List[str]:
        """获取 Agent 的能力列表"""
        try:
            result = db.execute(text("""
                SELECT capabilities FROM agents WHERE id = :agent_id
            """), {"agent_id": agent_id}).fetchone()

            if result:
                import json
                capabilities = result[0]
                if isinstance(capabilities, str):
                    return json.loads(capabilities)
                return capabilities or []
            return []
        except Exception as e:
            logger.error(f"[TaskAssigner] _get_agent_capabilities error for {agent_id}: {e}")
            return []

    def assign_pending_tasks(self) -> Dict[str, Any]:
        """
        分配待处理任务
        
        逻辑（Phase 2 增强版）：
        1. 查询所有待分配任务（按优先级排序）
        2. 对每个任务：
           a. 如果任务有 capability_tags → 调用匹配引擎选 Agent
           b. 如果无 capability_tags 或匹配失败 → fallback 到负载选择
        3. 检查选中 Agent 是否有空余 slot
        4. 分配执行者，同时分配验证者（needs_verification=True 时）
        5. 更新状态，更新 Agent 的 current_tasks
        
        Sprint 85 增强：同时分配 verifier_agent_id，且 verifier ≠ executor
        """
        assigned_count = 0

        try:
            with self.db.engine.connect() as conn:
                # 获取所有待分配任务（依赖全部完成 + 优先级排序）
                # 包含 Task 级别依赖检查 + Project 级别依赖链检查
                pending_tasks = conn.execute(text("""
                    SELECT 
                        t.id, t.title, t.priority, t.assigned_agent,
                        t.capability_tags, t.needs_verification, t.verifier_agent_id
                    FROM tasks t
                    WHERE t.status IN ('todo', 'pending', 'waiting')
                      AND (
                          -- 待分配执行者
                          t.assigned_agent IS NULL
                          -- 或执行者离线
                          OR EXISTS (
                              SELECT 1 FROM agents a 
                              WHERE a.id = t.assigned_agent 
                              AND a.health_status != 'online'
                          )
                          -- 或已有执行者在线但任务仍为 todo（需要推进到 in_progress）
                          OR (
                              t.assigned_agent IS NOT NULL
                              AND EXISTS (
                                  SELECT 1 FROM agents a2
                                  WHERE a2.id = t.assigned_agent
                                    AND a2.health_status = 'online'
                              )
                          )
                          -- 或需要验证但尚未分配验证者
                          OR (t.needs_verification = 1 AND t.verifier_agent_id IS NULL)
                      )
                      -- Task 级别依赖检查
                      AND NOT EXISTS (
                          SELECT 1 FROM task_dependencies td
                          JOIN tasks dep ON td.dependency_id = dep.id
                          WHERE td.task_id = t.id AND dep.status != 'done'
                      )
                      -- Project 级别依赖链检查：父 Project 的所有依赖 Project 必须全部完成
                      AND NOT EXISTS (
                          SELECT 1 
                          FROM projects parent_proj
                          JOIN projects dep_proj ON dep_proj.id = parent_proj.depends_on
                          WHERE parent_proj.id = t.project_id
                            AND dep_proj.status != 'done'
                      )
                    ORDER BY 
                        CASE t.priority 
                            WHEN 'critical' THEN 0
                            WHEN 'high' THEN 1 
                            WHEN 'medium' THEN 2 
                            WHEN 'low' THEN 3 
                            ELSE 4 
                        END,
                        t.created_at ASC
                """)).fetchall()

                if not pending_tasks:
                    conn.commit()
                    return {"assigned_count": 0}

                # 缓存 Agent 配置（避免重复查询）
                agent_cache: Dict[str, Dict[str, int]] = {}

                def _get_agent_slots(agent_id: str) -> Optional[int]:
                    """获取 Agent 可用 slot 数（实时从 tasks 表算，不依赖 current_tasks 列）"""
                    if agent_id not in agent_cache:
                        row = conn.execute(text("""
                            SELECT max_concurrent_tasks FROM agents WHERE id = :aid
                        """), {"aid": agent_id}).fetchone()
                        if row:
                            agent_cache[agent_id] = {"max": row[0]}
                        else:
                            agent_cache[agent_id] = None
                    if agent_cache[agent_id] is None:
                        return None
                    c = agent_cache[agent_id]
                    # 实时从 tasks 表算 in_progress 任务数
                    actual = conn.execute(text("""
                        SELECT COUNT(*) FROM tasks
                        WHERE assigned_agent = :aid
                          AND status IN ('in_progress', 'running')
                    """), {"aid": agent_id}).scalar()
                    return max(0, c["max"] - (actual or 0))

                def _consume_slot(agent_id: str):
                    """消耗一个 slot（内存中）"""
                    if agent_id in agent_cache and agent_cache[agent_id]:
                        agent_cache[agent_id]["current"] += 1

                import json as _json

                for task_row in pending_tasks:
                    task_id, title, priority, assigned_agent_raw, cap_tags_raw, needs_verification, existing_verifier = task_row

                    # 解析 capability_tags
                    capability_tags = {}
                    if cap_tags_raw:
                        try:
                            capability_tags = _json.loads(cap_tags_raw) if isinstance(cap_tags_raw, str) else cap_tags_raw
                        except Exception:
                            capability_tags = {}

                    # 用匹配引擎选择 Agent（有 capability_tags 走匹配，无则走负载选择）
                    if capability_tags:
                        try:
                            from reins.scheduler.assigner.agent_matcher import match_for_task
                            match_results = match_for_task(capability_tags)
                        except Exception as e:
                            logger.warning(f"[TaskAssigner] match_for_task failed: {e}")
                            match_results = []
                        
                        # 遍历匹配结果，找第一个有 slot 的 Agent
                        chosen_agent_id = None
                        for match in match_results:
                            aid = match["agent_id"]
                            available = _get_agent_slots(aid)
                            if available and available > 0:
                                chosen_agent_id = aid
                                break
                        # 匹配引擎全满 → fallback 到负载选择
                        if not chosen_agent_id:
                            chosen_agent_id = _assign_agent(conn)
                    else:
                        # 已有执行者且在线 → 用已有 agent，不走负载选择
                        chosen_agent_id = assigned_agent_raw
                        if not chosen_agent_id:
                            chosen_agent_id = _assign_agent(conn)
                    
                    if not chosen_agent_id:
                        continue  # 没有可用 Agent

                    # Sprint 85: 同时分配验证者（needs_verification=True 且 verifier 为空时）
                    verifier_agent_id = existing_verifier  # 保留已有值
                    if needs_verification and not existing_verifier:
                        verifier_agent_id = _assign_verifier(conn, chosen_agent_id, capability_tags)
                        if verifier_agent_id:
                            logger.info(f"[TaskAssigner] Assigned verifier {verifier_agent_id} for task {task_id}")

                    # 分配任务：区分是否已有执行者
                    if not assigned_agent_raw:
                        # 未分配执行者 → 同时分配执行者 + 验证者
                        conn.execute(text("""
                            UPDATE tasks
                            SET status = 'in_progress',
                                assigned_agent = :agent_id,
                                verifier_agent_id = :verifier_id,
                                started_at = :started_at,
                                updated_at = :now
                            WHERE id = :task_id
                              AND status IN ('todo', 'pending', 'waiting')
                        """), {
                            "task_id": task_id,
                            "agent_id": chosen_agent_id,
                            "verifier_id": verifier_agent_id,
                            "started_at": int(datetime.now().timestamp()),
                            "now": int(datetime.now().timestamp())
                        })
                        _consume_slot(chosen_agent_id)
                        assigned_count += 1
                    else:
                        # 已有执行者且在线 → 推进到 in_progress（如果还是 todo）
                        # 同时分配验证者
                        now_ts = int(datetime.now().timestamp())
                        conn.execute(text("""
                            UPDATE tasks
                            SET status = 'in_progress',
                                verifier_agent_id = COALESCE(:verifier_id, verifier_agent_id),
                                started_at = CASE WHEN started_at IS NULL THEN :started_at ELSE started_at END,
                                updated_at = :now
                            WHERE id = :task_id
                              AND status IN ('todo', 'pending', 'waiting')
                        """), {
                            "task_id": task_id,
                            "verifier_id": verifier_agent_id,
                            "started_at": now_ts,
                            "now": now_ts,
                        })
                        _consume_slot(chosen_agent_id)
                        assigned_count += 1
                        logger.info(f"[TaskAssigner] Dispatched existing task {task_id} to in_progress (agent={chosen_agent_id})")

                # 批量更新所有被分配 Agent 的 current_tasks + load
                updated_agents = set()
                for aid, info in agent_cache.items():
                    if info:
                        # 实时从 tasks 表算 in_progress 任务数，写入 current_tasks（不再依赖内存缓存的增量）
                        actual = conn.execute(text("""
                            SELECT COUNT(*) FROM tasks
                            WHERE assigned_agent = :aid
                              AND status IN ('in_progress', 'running')
                        """), {"aid": aid}).scalar()
                        conn.execute(text("""
                            UPDATE agents
                            SET current_tasks = :ct,
                                updated_at = :now
                            WHERE id = :aid
                        """), {
                            "aid": aid,
                            "ct": actual or 0,
                            "now": datetime.now()
                        })
                        update_agent_load(conn, aid)

                conn.commit()
                return {"assigned_count": assigned_count}
        except Exception as e:
            logger.error(f"[TaskAssigner] assign_pending_tasks error: {e}")
            return {"assigned_count": 0}

    def redistribute_recovered(self) -> Dict[str, Any]:
        """
        重新分配 recovery_count > 0 的任务
        
        逻辑：
        1. 找到 recovery_count > 0 的待处理任务
        2. 检查 max_retries (默认 3)
        3. 重新分配给负载最低的在线 Agent
        """
        redistributed_count = 0
        max_retries = 3

        try:
            with self.db.engine.connect() as conn:
                # 找到需要重新分配的任务
                tasks = conn.execute(text("""
                    SELECT id, title, assigned_agent, recovery_count
                    FROM tasks
                    WHERE recovery_count > 0
                      AND recovery_count < :max_retries
                      AND status IN ('todo', 'pending')
                """), {"max_retries": max_retries}).fetchall()

                for task in tasks:
                    task_id, title, assigned_agent, recovery_count = task

                    # 获取负载最低的在线 Agent
                    new_agent_id = self._get_lowest_load_online_agent(conn)
                    if not new_agent_id:
                        break

                    # 更新任务
                    conn.execute(text("""
                        UPDATE tasks
                        SET assigned_agent = :agent_id,
                            recovery_count = recovery_count + 1,
                            started_at = NULL,
                            status = 'todo',
                            paused_reason = NULL,
                            updated_at = :now
                        WHERE id = :task_id
                    """), {
                        "task_id": task_id,
                        "agent_id": new_agent_id,
                        "now": datetime.now()
                    })

                    # 更新新 Agent 的 current_tasks（实时从 tasks 表算 in_progress 任务数，不再手动 +1）
                    actual_new = conn.execute(text("""
                        SELECT COUNT(*) FROM tasks
                        WHERE assigned_agent = :agent_id
                          AND status IN ('in_progress', 'running')
                    """), {"agent_id": new_agent_id}).scalar()
                    conn.execute(text("""
                        UPDATE agents
                        SET current_tasks = :ct,
                            updated_at = :now
                        WHERE id = :agent_id
                    """), {
                        "agent_id": new_agent_id,
                        "ct": actual_new or 0,
                        "now": datetime.now()
                    })
                    update_agent_load(conn, new_agent_id)

                    # 如果原 Agent 存在，重新算其 current_tasks（实时从 tasks 表算）
                    if assigned_agent:
                        actual_old = conn.execute(text("""
                            SELECT COUNT(*) FROM tasks
                            WHERE assigned_agent = :agent_id
                              AND status IN ('in_progress', 'running')
                        """), {"agent_id": assigned_agent}).scalar()
                        conn.execute(text("""
                            UPDATE agents
                            SET current_tasks = :ct,
                                updated_at = :now
                            WHERE id = :agent_id
                        """), {
                            "agent_id": assigned_agent,
                            "ct": actual_old or 0,
                            "now": datetime.now()
                        })
                        update_agent_load(conn, assigned_agent)

                    redistributed_count += 1

                conn.commit()
                return {"redistributed_count": redistributed_count}
        except Exception as e:
            logger.error(f"[TaskAssigner] redistribute_recovered error: {e}")
            return {"redistributed_count": 0}
