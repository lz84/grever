"""
任务恢复器

Phase 2: 实现 TaskRecoverer 类
- recover_from_offline(agent_id): 恢复离线 Agent 的任务
- recover_from_timeout(): 恢复超时任务
- recover_single(task_id): 恢复单个任务
- recover_paused_tasks(): 恢复 paused 状态的任务
"""
from loguru import logger

from datetime import datetime, timedelta
from typing import List, Dict, Any

from reins.scheduler.statemachine import TaskStateMachine

from reins.common.config import TASK_TIMEOUT_MINUTES

from models import Task, Agent

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
            session = self.db.get_session()
            try:
                # 恢复 todo/pending 状态的任务
                todo_tasks = session.query(Task).filter(
                    Task.assigned_agent == agent_id,
                    Task.status.in_(['todo', 'pending'])
                ).all()
                for task in todo_tasks:
                    task.recovery_count = (task.recovery_count or 0) + 1
                    task.paused_reason = None
                    task.updated_at = datetime.now()

                # 恢复 in_progress 状态的任务 → paused（孤儿）
                in_progress_tasks = session.query(Task).filter(
                    Task.assigned_agent == agent_id,
                    Task.status == 'in_progress'
                ).all()
                for task in in_progress_tasks:
                    task.paused_reason = 'orphan_on_offline'
                    task.started_at = None
                    task.updated_at = int(datetime.now().timestamp())
                    # 使用状态机更新状态
                    fsm = TaskStateMachine(self.db, task.id)
                    fsm.transition('paused', reason='orphan_on_offline', extra={
                        'paused_reason': 'orphan_on_offline',
                        'started_at': None,
                        'updated_at': int(datetime.now().timestamp()),
                    })

                # 更新 Agent 的 current_tasks
                agent = session.query(Agent).filter(Agent.id == agent_id).first()
                if agent:
                    agent.current_tasks = 0
                    agent.updated_at = datetime.now()

                session.commit()
                return len(todo_tasks) + len(in_progress_tasks)
            finally:
                session.close()
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
        cutoff_ts = int((datetime.now() - timedelta(minutes=self.TASK_TIMEOUT)).timestamp())
        logger.info(f"[TaskRecoverer] recover_from_timeout: cutoff_ts={cutoff_ts}, timeout={self.TASK_TIMEOUT}min")

        try:
            session = self.db.get_session()
            try:
                # 查找超时任务（started_at 是 int Unix timestamp，cutoff 也必须是 int）
                timeout_tasks = session.query(Task).filter(
                    Task.status == 'in_progress',
                    Task.started_at.isnot(None),
                    Task.started_at < cutoff_ts
                ).all()
                logger.info(f"[TaskRecoverer] Found {len(timeout_tasks)} timeout tasks")
                for t in timeout_tasks:
                    logger.info(f"[TaskRecoverer] TIMEOUT: id={t.id}, started_at={t.started_at}, cutoff={cutoff_ts}")

                recovered_count = 0
                for task in timeout_tasks:
                    task_id = task.id
                    agent_id = task.assigned_agent

                    # 使用状态机更新任务状态为 paused（自动写 activity log）
                    fsm = TaskStateMachine(self.db, task_id)
                    fsm.transition('paused', reason='orphan_on_timeout', extra={
                        'paused_reason': 'orphan_on_timeout',
                        'result_summary': '任务超时未完成，已暂停等待重试',
                    })

                    # 更新 Agent 的 current_tasks
                    if agent_id:
                        agent = session.query(Agent).filter(Agent.id == agent_id).first()
                        if agent:
                            agent.current_tasks = max(0, agent.current_tasks - 1)
                            agent.updated_at = datetime.now()

                    recovered_count += 1

                session.commit()
                return recovered_count
            finally:
                session.close()
        except Exception as e:
            logger.error(f"[TaskRecoverer] recover_from_timeout error: {e}")
            return 0

    def recover_single(self, task_id: str) -> bool:
        """
        恢复单个任务
        
        将任务从异常状态恢复到 todo 状态，清除 assigned_agent
        """
        try:
            session = self.db.get_session()
            try:
                # 获取任务信息
                task = session.query(Task).filter(Task.id == task_id).first()
                if not task:
                    return False

                status = task.status
                assigned_agent = task.assigned_agent

                # 如果是异常状态，恢复任务
                if status in ('timeout', 'blocked', 'cancelled'):
                    # 使用状态机更新为 todo
                    fsm = TaskStateMachine(self.db, task_id)
                    extra = {
                        "assigned_agent": None,
                        "updated_at": int(datetime.now().timestamp())
                    }
                    fsm.transition("todo", reason="recover_single", extra=extra)

                    # 更新 Agent 的 current_tasks
                    if assigned_agent:
                        agent = session.query(Agent).filter(Agent.id == assigned_agent).first()
                        if agent:
                            agent.current_tasks = max(0, agent.current_tasks - 1)
                            agent.updated_at = datetime.now()

                session.commit()
                return True
            finally:
                session.close()
        except Exception as e:
            logger.error(f"[TaskRecoverer] recover_single error for {task_id}: {e}")
            return False

    def recover_paused_tasks(self) -> int:
        """
        恢复 paused 状态的任务
        
        动作：
        - recovery_count < max_retries (默认3) → 恢复为 todo，recovery_count += 1
        - recovery_count >= max_retries → 标记为 failed
        - 清理 paused_reason 和 assigned_agent
        - 对应 agent 的 current_tasks 减少
        """
        max_retries = 3
        recovered_count = 0
        
        try:
            session = self.db.get_session()
            try:
                # 查询所有 paused 任务（有 paused_reason 的）
                paused_tasks = session.query(Task).filter(
                    Task.status == 'paused',
                    Task.paused_reason.isnot(None)
                ).all()
                
                for task in paused_tasks:
                    recovery_count = task.recovery_count or 0
                    original_agent_id = task.assigned_agent  # 保存原 Agent ID（重置前）
                    
                    # 使用状态机更新任务状态
                    fsm = TaskStateMachine(self.db, task.id)
                    if recovery_count < max_retries:
                        # 恢复为 todo，重置状态
                        extra = {
                            "recovery_count": recovery_count + 1,
                            "paused_reason": None,
                            "assigned_agent": None,
                            "started_at": None,
                            "updated_at": int(datetime.now().timestamp())
                        }
                        fsm.transition("todo", reason="paused 恢复", extra=extra)
                        logger.info(f"[TaskRecoverer] Recovered paused task {task.id}, recovery_count={task.recovery_count}")
                        
                        # 更新原 Agent 的 current_tasks（用保存的 original_agent_id）
                        if original_agent_id:
                            actual_tasks = session.query(Task).filter(
                                Task.assigned_agent == original_agent_id,
                                Task.status.in_(['in_progress', 'running'])
                            ).count()
                            session.query(Agent).filter(Agent.id == original_agent_id).update({
                                Agent.current_tasks: max(0, actual_tasks),
                                Agent.updated_at: datetime.now()
                            })
                    else:
                        # 超过最大恢复次数，标记为 failed
                        extra = {
                            "error_message": '超过最大恢复次数',
                            "paused_reason": None,
                            "assigned_agent": None,
                            "updated_at": int(datetime.now().timestamp())
                        }
                        fsm.transition("failed", reason="最大恢复次数超限", extra=extra)
                        logger.info(f"[TaskRecoverer] Task {task.id} failed: max retries exceeded")
                        
                        # 更新原 Agent 的 current_tasks（用保存的 original_agent_id）
                        if original_agent_id:
                            session.query(Agent).filter(Agent.id == original_agent_id).update({
                                Agent.current_tasks: 0,
                                Agent.updated_at: datetime.now()
                            })
                    
                    recovered_count += 1
                
                session.commit()
            finally:
                session.close()
            return recovered_count
        except Exception as e:
            logger.error(f"[TaskRecoverer] recover_paused_tasks error: {e}")
            return 0
