"""
Grever 核心调度引擎

Phase 1: 启动/停止 + 空 tick 循环（仅刷新统计）
Phase 2: 实现完整的调度逻辑
Phase 3: 主动推送执行架构（Sprint 74）- ProjectExecutor
"""

import asyncio
import json
import subprocess
import sys
from loguru import logger
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Task, Goal, Project
from models.human_input import HumanInputRequest
from reins.scheduler.stats import SchedulerStats
from reins.scheduler.health_manager import AgentHealthManager
from reins.scheduler.task_recoverer import TaskRecoverer
from reins.scheduler.task_assigner import TaskAssigner
from reins.scheduler.dependency_resolver import DependencyResolver
from reins.scheduler.result_verifier import ResultVerifier
from reins.scheduler.project_executor import ProjectExecutor
from reins.scheduler.statemachine import TaskStateMachine, ProjectStateMachine, GoalStateMachine
from reins.common.config import TICK_INTERVAL, STALE_THRESHOLD, OFFLINE_THRESHOLD, TASK_TIMEOUT_MINUTES
import subprocess
import sys
from loguru import logger
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Task, Goal, Project
from models.human_input import HumanInputRequest
from reins.scheduler.stats import SchedulerStats
from reins.scheduler.health_manager import AgentHealthManager
from reins.scheduler.task_recoverer import TaskRecoverer
from reins.scheduler.task_assigner import TaskAssigner
from reins.scheduler.dependency_resolver import DependencyResolver
from reins.scheduler.result_verifier import ResultVerifier
from reins.scheduler.project_executor import ProjectExecutor

class GreverScheduler:
    """
    Grever 核心调度引擎

    职责（Phase 3 实现）：
    - 统一管理 Agent 健康度
    - 主动分配/回收/重新分配任务
    - 监控任务超时
    - 解锁依赖关系
    - 项目级执行管理（Sprint 74）
    - 生成调度报告
    """

    TICK_INTERVAL = TICK_INTERVAL  # 每 N 秒执行一次

    # 健康度阈值（秒）
    STALE_THRESHOLD = STALE_THRESHOLD  # N 秒无心跳 → stale
    OFFLINE_THRESHOLD = OFFLINE_THRESHOLD  # N 秒无心跳 → offline

    # 任务超时（分钟）— 单一事实源：reins.config.TASK_TIMEOUT_MINUTES
    TASK_TIMEOUT = TASK_TIMEOUT_MINUTES

    def __init__(self, db_manager):
        self.db = db_manager
        self.stats = SchedulerStats()
        self.health_manager = AgentHealthManager(db_manager)
        self.task_recoverer = TaskRecoverer(db_manager)
        self.task_assigner = TaskAssigner(db_manager)
        self.dependency_resolver = DependencyResolver(db_manager)
        self.result_verifier = ResultVerifier(db_manager)
        
        # Sprint 120: 空转 backoff 计数器
        self._consecutive_idle_ticks = 0
        
        # Sprint 74: ProjectExecutor 池
        # Dict[str, ProjectExecutor] — 项目执行器池
        self.project_executors: Dict[str, ProjectExecutor] = {}
        
        self._running = False
        self._task: asyncio.Task | None = None

        # Sprint 105-2: daily distillation tracking
        self._last_distill_date: Optional[str] = None

    async def start(self):
        """启动调度循环（server.py 启动时调用）"""
        # 启动时清理所有 in_progress 任务（server 重启后不可能有 agent 在跑）
        self._cleanup_stale_tasks()
        
        self._running = True
        self._task = asyncio.create_task(self._tick_loop())
        logger.info("[Scheduler] Started (interval=30s)")
        logger.info("[Reins API] Scheduler started")

    def _cleanup_stale_tasks(self):
        """
        清理残留的 in_progress 任务
        
        server 重启后，所有 in_progress 任务都视为孤儿：
        - agent 进程已死（server 重启杀掉了所有子进程）
        - 不可能"重跑恢复"（会重复执行）
        → 设置 status = 'paused', paused_reason = 'orphan_on_restart'
        
        如果业务需要重跑，应该由人工决策，不应该自动重置。
        """
        try:
            session = self.db.get_session()
            try:
                stale_tasks = session.query(Task).filter(Task.status == 'in_progress').all()
                for task in stale_tasks:
                    try:
                        TaskStateMachine(db, task.id).transition(
                            'paused',
                            reason='orphan_on_restart: scheduler restart cleanup',
                            extra={'paused_reason': 'orphan_on_restart'},
                        )
                    except Exception as e:
                        logger.warning(f"[Scheduler] orphan cleanup failed for {task.id}: {e}")
                session.commit()
                if stale_tasks:
                    logger.info(f"[Scheduler] Cleaned up {len(stale_tasks)} stale in_progress tasks -> paused (orphan_on_restart)")
            finally:
                session.close()
        except Exception as e:
            logger.error(f"[Scheduler] Failed to cleanup stale tasks: {e}")

    async def stop(self):
        """停止调度循环"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[Scheduler] Stopped")
        logger.info("[Reins API] Scheduler stopped")

    async def _tick_loop(self):
        """调度主循环"""
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"[Scheduler] Tick error: {e}")
            base = self.TICK_INTERVAL
            backoff = min(base * (2 ** self._consecutive_idle_ticks), 300)  # max 5min
            await asyncio.sleep(backoff)

    async def _tick(self):
        """
        一次完整的调度周期（10步）

        Step 1: 健康扫描 - 扫描所有 Agent，更新健康状态
        Step 2: 超时恢复 - 恢复超时任务
        Step 3: 离线恢复 - 恢复离线 Agent 的任务
        Step 4: 重新分配 - 重新分配 recovery_count > 0 的任务
        Step 4.1: 分配新任务 - 给新实例化的 assigned_agent=NULL 的任务分配智能体
        Step 4.5: HITL 检查 - 处理 pending 的人类输入请求
        Step 5: 项目执行器 tick - 主动推送执行架构（Sprint 74）
        Step 6: 解锁依赖 - 解锁依赖任务（stub）
        Step 7: 验证器 tick - 扫描 review_needed 任务并验证
        Step 8: 权重衰减 - 能力标签权重衰减
        Step 9: 统计更新 - 更新调度统计
        """
        step_results = {}

        # Step 1: 健康扫描
        try:
            health_result = self.health_manager.scan()
            step_results["health"] = health_result
            logger.info(f"[Scheduler] Tick {self.stats.total_ticks + 1}: health scan - {health_result}")
        except Exception as e:
            logger.error(f"[Scheduler] Tick {self.stats.total_ticks + 1}: health scan error: {e}")
            step_results["health"] = {"online_count": 0, "stale_count": 0, "offline_count": 0}

        # Step 2: 超时恢复
        try:
            timeout_result = self.task_recoverer.recover_from_timeout()
            step_results["recover"] = {"recovered_count": timeout_result}
            if timeout_result > 0:
                logger.info(f"[Scheduler] Tick {self.stats.total_ticks + 1}: recovered {timeout_result} timeout tasks")
        except Exception as e:
            logger.error(f"[Scheduler] Tick {self.stats.total_ticks + 1}: timeout recover error: {e}")
            step_results["recover"] = {"recovered_count": 0}

        # Step 3: 离线恢复
        try:
            offline_agents = self.health_manager.get_offline_agents()
            for agent_id in offline_agents:
                recovered = self.task_recoverer.recover_from_offline(agent_id)
                step_results["recover"] = step_results.get("recover", {})
                step_results["recover"]["recovered_count"] = step_results["recover"].get("recovered_count", 0) + recovered
                if recovered > 0:
                    logger.info(f"[Scheduler] Tick {self.stats.total_ticks + 1}: recovered {recovered} tasks from {agent_id}")
        except Exception as e:
            logger.error(f"[Scheduler] Tick {self.stats.total_ticks + 1}: offline recover error: {e}")

        # Step 4: 重新分配
        try:
            redistribute_result = self.task_assigner.redistribute_recovered()
            step_results["assign"] = step_results.get("assign", {})
            step_results["assign"]["redistributed_count"] = redistribute_result.get("redistributed_count", 0)
            if redistribute_result.get("redistributed_count", 0) > 0:
                logger.info(f"[Scheduler] Tick {self.stats.total_ticks + 1}: redistributed {redistribute_result.get('redistributed_count')} tasks")
        except Exception as e:
            logger.error(f"[Scheduler] Tick {self.stats.total_ticks + 1}: redistribute error: {e}")
            step_results["assign"] = step_results.get("assign", {})
            step_results["assign"]["redistributed_count"] = 0

        # Step 4.2: 恢复 paused 任务
        try:
            paused_result = self.task_recoverer.recover_paused_tasks()
            step_results["recover_paused"] = {"recovered_count": paused_result}
            if paused_result > 0:
                logger.info(f"[Scheduler] Recovered {paused_result} paused tasks")
        except Exception as e:
            logger.error(f"[Scheduler] recover_paused_tasks error: {e}")
            step_results["recover_paused"] = {"recovered_count": 0}

        # Step 4.1: 分配新任务（assign_pending_tasks）
        # 从场景实例化后的任务 assigned_agent=NULL，需要被分配给智能体
        try:
            pending_result = self.task_assigner.assign_pending_tasks()
            pending_count = pending_result.get("assigned_count", 0)
            step_results["assign_new"] = {"assigned_count": pending_count}
            if pending_count > 0:
                logger.info(f"[Scheduler] Tick {self.stats.total_ticks + 1}: assign_pending_tasks - assigned {pending_count} tasks")
        except Exception as e:
            logger.error(f"[Scheduler] Tick {self.stats.total_ticks + 1}: assign_pending_tasks error: {e}")
            step_results["assign_new"] = {"assigned_count": 0}

        # Step 4.5: HITL 检查（处理 pending 的人类输入请求）
        try:
            hitl_result = self._tick_hitl_check()
            step_results["hitl"] = hitl_result
            if hitl_result.get("paused", 0) > 0 or hitl_result.get("timeout_handled", 0) > 0:
                logger.info(f"[Scheduler] HITL: paused={hitl_result['paused']}, timeout={hitl_result['timeout_handled']}")
        except Exception as e:
            logger.error(f"[Scheduler] HITL check error: {e}")
            step_results["hitl"] = {"errors": 1}

        # Sprint 74: Step 5 - 项目执行器 tick（主动推送执行架构）
        try:
            project_results = await self._tick_project_executors()
            step_results["project_executors"] = project_results
            if project_results.get("total_completed", 0) > 0:
                logger.info(f"[Scheduler] Tick {self.stats.total_ticks + 1}: project_executors - completed {project_results['total_completed']} tasks")
            if project_results.get("total_launched", 0) > 0:
                logger.info(f"[Scheduler] Tick {self.stats.total_ticks + 1}: project_executors - launched {project_results['total_launched']} tasks")
        except Exception as e:
            logger.error(f"[Scheduler] Tick {self.stats.total_ticks + 1}: project_executors error: {e}")
            step_results["project_executors"] = {"total_completed": 0, "total_launched": 0}

        # Step 6: 依赖解锁（扫描 blocked 任务 + 检查新完成的任务）
        try:
            unlocked = self.dependency_resolver.scan_blocked()
            step_results["unlock"] = {"unlocked_count": len(unlocked), "task_ids": unlocked}
            logger.info(f"[Scheduler] Tick {self.stats.total_ticks + 1}: unlock - scanned {len(unlocked)} tasks")
        except Exception as e:
            logger.error(f"[Scheduler] Tick {self.stats.total_ticks + 1}: unlock error: {e}")
            step_results["unlock"] = {"unlocked_count": 0}

        # Step 7: 验证器 tick - 扫描 review_needed 任务并验证
        try:
            verify_result = self.result_verifier.tick()
            step_results["verifier"] = verify_result
            if verify_result.get("processed_count", 0) > 0:
                logger.info(f"[Scheduler] Tick {self.stats.total_ticks + 1}: verifier - processed {verify_result['processed_count']} tasks")
        except Exception as e:
            logger.error(f"[Scheduler] Tick {self.stats.total_ticks + 1}: verifier error: {e}")
            step_results["verifier"] = {"processed_count": 0}

        # Step 8: 权重衰减（能力标签）
        try:
            from reach.industry.auto_tagging import decay_weights
            decay_result = decay_weights()
            if decay_result.get("decayed_count", 0) > 0 or decay_result.get("removed_count", 0) > 0:
                logger.info(f"[Scheduler] Tag decay: {decay_result}")
        except Exception as e:
            logger.error(f"[Scheduler] Tag decay error: {e}")

        # Step 9: 统计更新
        try:
            self.stats.refresh_task_stats(self.db)
            self.stats.update(step_results)
            logger.info(f"[Scheduler] Tick {self.stats.total_ticks}: {self.stats.summary()}")
        except Exception as e:
            logger.error(f"[Scheduler] Tick {self.stats.total_ticks + 1}: stats update error: {e}")

        # Sprint 120: 计算空转 tick 计数（只算真正处理的任务量，不含健康扫描）
        total_processed = (
            step_results.get("recover", {}).get("recovered_count", 0)
            + step_results.get("assign", {}).get("redistributed_count", 0)
            + step_results.get("assign_new", {}).get("assigned_count", 0)
            + step_results.get("project_executors", {}).get("total_completed", 0)
            + step_results.get("project_executors", {}).get("total_launched", 0)
            + step_results.get("verifier", {}).get("processed_count", 0)
            + step_results.get("recover_paused", {}).get("recovered_count", 0)
            + step_results.get("unlock", {}).get("unlocked_count", 0)
            + step_results.get("hitl", {}).get("timeout_handled", 0)
        )
        if total_processed == 0:
            self._consecutive_idle_ticks += 1
        else:
            self._consecutive_idle_ticks = 0

        # Step 10: 每日蒸馏（Sprint 105-2）- 凌晨 02:00 触发
        try:
            await self._tick_daily_distill()
        except Exception as e:
            logger.error(f"[Scheduler] Daily distill error: {e}")

    async def _tick_project_executors(self) -> Dict[str, int]:
        """
        Sprint 74: tick 所有项目执行器
        
        逻辑：
        1. 查询所有活跃项目（active/in_progress）
        2. 为每个项目创建/获取 ProjectExecutor
        3. 为 project_id IS NULL 的任务创建 "Grever 内部" 项目
        4. 调用每个 executor 的 tick()
        5. 清理已完成的项目 executor
        
        返回：
            {"total_completed": int, "total_launched": int}
        """
        total_completed = 0
        total_launched = 0
        
        try:
            session = self.db.get_session()
            try:
                # 查询所有活跃项目
                active_projects = session.query(Project).filter(
                    Project.status.in_(['active', 'in_progress'])
                ).all()
                
                # 额外检查：是否有 project_id IS NULL 的任务
                null_projects = session.query(func.count(Task.id)).filter(Task.project_id.is_(None)).scalar() or 0
                
                project_ids = [p.id for p in active_projects]
                
                # 如果有 NULL project_id 的任务，确保 "Grever 内部" 项目存在
                if null_projects > 0:
                    internal_project_id = "proj-grever-internal"
                    existing = session.query(Project.id).filter(Project.id == internal_project_id).first()
                    
                    if not existing:
                        # 创建 "Grever 内部" 项目（仅在 migration 未执行时）
                        new_project = Project(
                            id=internal_project_id,
                            name="Grever 内部",
                            description="Grever 系统内部任务项目",
                            status="active",
                        )
                        session.add(new_project)
                        session.commit()
                        project_ids.append(internal_project_id)
                        logger.info(f"[Scheduler] Created internal project {internal_project_id} for NULL project tasks")
                    else:
                        project_ids.append(internal_project_id)
                
                logger.info(f"[Scheduler] Tick {self.stats.total_ticks + 1}: found {len(project_ids)} active projects: {project_ids}")
                
                # 为每个项目 tick
                for project_id in project_ids:
                    try:
                        # 获取或创建 ProjectExecutor
                        executor = self.project_executors.get(project_id)
                        if not executor:
                            executor = ProjectExecutor(project_id, self.db)
                            self.project_executors[project_id] = executor
                            logger.info(f"[Scheduler] Created ProjectExecutor for project {project_id}")
                        
                        # tick 项目执行器
                        result = await executor.tick()
                        
                        # 累加统计
                        for r in result.get("completed", []):
                            total_completed += 1
                        
                        total_launched += result.get("launched", 0)
                        
                        # 检查是否完成
                        if executor.is_completed():
                            logger.info(f"[Scheduler] Project {project_id} completed, removing executor")
                            del self.project_executors[project_id]
                            
                    except Exception as e:
                        tb = traceback.format_exc()
                        logger.info(f"[Scheduler] FAILED to tick project {project_id}: {e}\n{tb}", flush=True)
                        logger.error(f"[Scheduler] Failed to tick project {project_id}: {e}\n{tb}")
                        # 最好继续处理其他项目，不中断
                        continue
                
                # 清理已完成的 executor（已完成但未被标记删除的）
                completed_projects = []
                for pid, executor in self.project_executors.items():
                    if executor.state == 'completed':
                        completed_projects.append(pid)
                
                for pid in completed_projects:
                    del self.project_executors[pid]
                    logger.info(f"[Scheduler] Cleaned up completed executor for project {pid}")
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"[Scheduler] _tick_project_executors error: {e}")
        
        return {
            "total_completed": total_completed,
            "total_launched": total_launched,
        }

    def _tick_hitl_check(self) -> Dict:
        """
        HITL 检查：处理 pending 的人类输入请求

        逻辑：
        1. 查询所有 status='pending' 的 human_input_requests
        2. 对每个请求：
           a. 检查是否超时（created_at + timeout_minutes < now）
           b. 如果超时 → 执行 timeout_action
           c. 如果未超时 → 暂停关联的 Goal/Project/Task
        """
        results = {"paused": 0, "timeout_handled": 0, "errors": 0}

        try:
            session = self.db.get_session()
            try:
                pending = session.query(HumanInputRequest).filter(
                    HumanInputRequest.status == 'pending'
                ).all()

                for req in pending:
                    req_id = req.id
                    task_id = req.task_id
                    goal_id = req.goal_id
                    project_id = req.project_id
                    timeout_action = req.timeout_action
                    timeout_minutes = req.timeout_minutes or 30
                    default_value = req.default_value
                    branches_raw = req.branches
                    created_at = req.created_at

                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at)

                    timeout_at = created_at + timedelta(minutes=timeout_minutes)
                    is_timed_out = datetime.now() > timeout_at

                    if is_timed_out:
                        try:
                            self._handle_hitl_timeout(
                                session, req_id, task_id, goal_id, project_id,
                                timeout_action, default_value, branches_raw
                            )
                            results["timeout_handled"] += 1
                        except Exception as e:
                            logger.error(f"[HITL] Timeout handling error for {req_id}: {e}")
                            results["errors"] += 1
                    else:
                        try:
                            now = datetime.now()
                            if goal_id:
                                session.query(Goal).filter(
                                    Goal.id == goal_id,
                                    Goal.status.notin_(['completed', 'failed'])
                                ).update({
                                    "status": "paused",
                                    "paused_reason": "awaiting_human_input",
                                    "updated_at": now
                                }, synchronize_session=False)
                            if project_id:
                                session.query(Project).filter(
                                    Project.id == project_id,
                                    Project.status.notin_(['completed', 'failed'])
                                ).update({
                                    "status": "paused",
                                    "paused_reason": "awaiting_human_input",
                                    "updated_at": now
                                }, synchronize_session=False)
                            if task_id:
                                task = session.query(Task).filter(Task.id == task_id).first()
                                if task and task.status not in ['done', 'failed']:
                                    TaskStateMachine(db, task_id).transition(
                                        'paused',
                                        reason='awaiting_human_input',
                                        extra={'paused_reason': 'awaiting_human_input'},
                                    )
                            results["paused"] += 1
                        except Exception as e:
                            logger.error(f"[HITL] Pause error for {req_id}: {e}")
                            results["errors"] += 1

                session.commit()
            finally:
                session.close()
        except Exception as e:
            logger.error(f"[HITL] Check error: {e}")
            results["errors"] += 1

        return results

    def _handle_hitl_timeout(self, session, req_id, task_id, goal_id, project_id,
                              timeout_action, default_value, branches_raw):
        """处理 HITL 超时"""
        now = datetime.now()

        if timeout_action == 'use_default' and default_value:
            # 使用默认值，相当于人类提交了 default_value
            session.query(HumanInputRequest).filter(HumanInputRequest.id == req_id).update({
                "status": "submitted",
                "input_data": json.dumps({"value": default_value}),
                "response": default_value,
                "submitted_at": now,
                "updated_at": now
            }, synchronize_session=False)

            # 如果是 task_id，解锁依赖
            if task_id:
                resolver = DependencyResolver(self.db)
                resolver.unlock_on_human_input(req_id)

        elif timeout_action in ('skip_project', 'skip_task'):
            session.query(HumanInputRequest).filter(HumanInputRequest.id == req_id).update({
                "status": "skipped",
                "updated_at": now
            }, synchronize_session=False)

        elif timeout_action == 'escalate':
            session.query(HumanInputRequest).filter(HumanInputRequest.id == req_id).update({
                "status": "escalated",
                "updated_at": now
            }, synchronize_session=False)
            logger.warning(f"[HITL] Escalated request {req_id} (no human response)")

            # 标记任务为 failed
            if task_id:
                TaskStateMachine(db, task_id).transition(
                    'failed',
                    reason='HITL timeout escalate',
                    extra={'escalated': True, 'hir_id': req_id},
                )

        # 恢复关联实体的状态
        if goal_id:
            goal_fsm = GoalStateMachine(session, goal_id)
            goal_fsm.transition("active", reason="HITL 超时后恢复")
        if project_id:
            project_fsm = ProjectStateMachine(session, project_id)
            project_fsm.transition("active", reason="HITL 超时后恢复")
        if task_id:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                TaskStateMachine(db, task_id).transition(
                    'todo',
                    reason='scheduler unpause',
                    extra={'paused_reason': None},
                )

    async def _tick_daily_distill(self):
        """
        Sprint 105-2: 每日定时蒸馏任务

        在凌晨 02:00 触发，回溯最近 7 天数据。
        每天只执行一次，通过 _last_distill_date 防重。
        如果采集到的任务记录不足 5 条则跳过。
        蒸馏失败不阻断其他定时任务（已在调用处 try/except）。
        """
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # 已经执行过，跳过
        if self._last_distill_date == today_str:
            return

        # 凌晨 02:00 之前不触发
        if now.hour < 2:
            return

        # 触发蒸馏
        logger.info(f"[Scheduler] Daily distillation triggered at {now.strftime('%Y-%m-%d %H:%M:%S')}")

        # 先检查是否有足够的任务记录
        try:
            session = self.db.get_session()
            try:
                cutoff_ts = int((now - timedelta(days=7)).timestamp())
                record_count = session.query(func.count(Task.id)).filter(
                    Task.status.in_(['done', 'failed', 'error', 'timeout']),
                    Task.assigned_agent.isnot(None),
                    Task.assigned_agent != '',
                    Task.completed_at >= cutoff_ts
                ).scalar() or 0
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"[Scheduler] Distill record count check failed: {e}, proceeding anyway")
            record_count = 5  # 如果检查失败，假设足够

        if record_count < 5:
            logger.info(f"No task records found, skipping distillation (only {record_count} records in last 7 days)")
            self._last_distill_date = today_str
            return

        # 确定 src 目录（trigger_distill.py 所在位置的父目录）
        src_dir = Path(__file__).parent.parent.parent  # .../reins/scheduler -> .../reins -> .../src
        if not src_dir.is_dir():
            # fallback: try relative to server package
            src_dir = Path(__file__).resolve().parent.parent.parent

        try:
            result = subprocess.run(
                [sys.executable, "-m", "evo.trigger_distill", "--lookback", "7"],
                cwd=str(src_dir),
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                logger.info(f"[Scheduler] Daily distillation completed successfully")
                if result.stdout.strip():
                    for line in result.stdout.strip().split("\n")[-5:]:
                        logger.info(f"[Distill] {line}")
            else:
                logger.warning(f"[Scheduler] Distillation returned code {result.returncode}")
                if result.stderr.strip():
                    logger.warning(f"[Distill stderr] {result.stderr.strip()[-500:]}")

            self._last_distill_date = today_str

        except subprocess.TimeoutExpired:
            logger.error("[Scheduler] Daily distillation timed out (300s)")
        except Exception as e:
            logger.error(f"[Scheduler] Daily distillation failed: {e}")
