"""
任务恢复器

Phase 2: 实现 TaskRecoverer 类
- recover_from_offline(agent_id): 恢复离线 Agent 的任务
- recover_from_timeout(): 恢复超时任务
- recover_single(task_id): 恢复单个任务
"""
from loguru import logger

from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy import text

from reins.common.config import TASK_TIMEOUT_MINUTES

class TaskRecoverer:
    """
    任务恢复器
    
    负责恢复因 Agent 离线或任务超时而中断的任务
    """

    # 任务超时阈值（分钟）— 单一事实源：reins.config.TASK_TIMEOUT_MINUTES
    TASK_TIMEOUT = TASK_TIMEOUT_MINUTES

    def __init__(self, db_manager):
        self.db = db_manager

    def recover_from_offline(self, agent_id: str) -> int:
        """
        Agent 离线时，恢复其分配的任务
        
        动作：
        - todo/pending: status = 'todo', recovery_count += 1
        - in_progress: status = 'paused', paused_reason = 'orphan_on_offline', started_at = NULL
        """
        try:
            with self.db.engine.connect() as conn:
                # 恢复 todo/pending 状态的任务（不清 assigned_agent）
                result1 = conn.execute(text("""
                    UPDATE tasks
                    SET status = 'todo',
                        recovery_count = COALESCE(recovery_count, 0) + 1,
                        updated_at = :now
                    WHERE assigned_agent = :agent_id
                      AND status IN ('todo', 'pending')
                """), {
                    "agent_id": agent_id,
                    "now": datetime.now()
                })

                # 恢复 in_progress 状态的任务 → paused（孤儿）
                # started_at = NULL 保持暂停时的现场
                result2 = conn.execute(text("""
                    UPDATE tasks
                    SET status = 'paused',
                        paused_reason = 'orphan_on_offline',
                        started_at = NULL,
                        updated_at = :now
                    WHERE assigned_agent = :agent_id
                      AND status = 'in_progress'
                """), {
                    "agent_id": agent_id,
                    "now": datetime.now()
                })

                # 更新 Agent 的 current_tasks
                conn.execute(text("""
                    UPDATE agents
                    SET current_tasks = 0,
                        updated_at = :now
                    WHERE id = :agent_id
                """), {
                    "agent_id": agent_id,
                    "now": datetime.now()
                })

                conn.commit()
                
                return result1.rowcount + result2.rowcount
        except Exception as e:
            logger.error(f"[TaskRecoverer] recover_from_offline error for {agent_id}: {e}")
            return 0

    def recover_from_timeout(self) -> int:
        """
        恢复超时任务
        
        查找 in_progress 任务中，started_at < (now - TIMEOUT) 的任务
        设置 status = 'paused', paused_reason = 'orphan_on_timeout'
        不再累加 recovery_count（暂停后由人工或定时器决定何时恢复）
        """
        cutoff = datetime.now() - timedelta(minutes=self.TASK_TIMEOUT)

        try:
            with self.db.engine.connect() as conn:
                # 查找超时任务
                timeout_tasks = conn.execute(text("""
                    SELECT id, title, assigned_agent, started_at
                    FROM tasks
                    WHERE status = 'in_progress'
                      AND started_at IS NOT NULL
                      AND started_at < :cutoff
                """), {"cutoff": cutoff}).fetchall()

                recovered_count = 0
                for task in timeout_tasks:
                    task_id, task_title, agent_id, started_at = task

                    # 1. 更新任务状态为 paused（孤儿超时）
                    conn.execute(text("""
                        UPDATE tasks
                        SET status = 'paused',
                            paused_reason = 'orphan_on_timeout',
                            updated_at = :now,
                            result_summary = '任务超时未完成，已暂停等待重试'
                        WHERE id = :task_id
                    """), {"task_id": task_id, "now": datetime.now()})

                    # 2. 更新 Agent 的 current_tasks
                    if agent_id:
                        conn.execute(text("""
                            UPDATE agents
                            SET current_tasks = MAX(0, current_tasks - 1),
                                updated_at = :now
                            WHERE id = :agent_id
                        """), {"agent_id": agent_id, "now": datetime.now()})

                    recovered_count += 1

                conn.commit()
                return recovered_count
        except Exception as e:
            logger.error(f"[TaskRecoverer] recover_from_timeout error: {e}")
            return 0

    def recover_single(self, task_id: str) -> bool:
        """
        恢复单个任务
        
        将任务从异常状态恢复到 todo 状态，清除 assigned_agent
        """
        try:
            with self.db.engine.connect() as conn:
                # 获取任务信息
                task = conn.execute(text("""
                    SELECT status, assigned_agent FROM tasks WHERE id = :task_id
                """), {"task_id": task_id}).fetchone()

                if not task:
                    return False

                status, assigned_agent = task

                # 如果是异常状态，恢复任务
                if status in ('timeout', 'blocked', 'cancelled'):
                    conn.execute(text("""
                        UPDATE tasks
                        SET status = 'todo',
                            assigned_agent = NULL,
                            updated_at = :now
                        WHERE id = :task_id
                    """), {"task_id": task_id, "now": datetime.now()})

                    # 更新 Agent 的 current_tasks
                    if assigned_agent:
                        conn.execute(text("""
                            UPDATE agents
                            SET current_tasks = MAX(0, current_tasks - 1),
                                updated_at = :now
                            WHERE id = :agent_id
                        """), {"agent_id": assigned_agent, "now": datetime.now()})

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"[TaskRecoverer] recover_single error for {task_id}: {e}")
            return False
