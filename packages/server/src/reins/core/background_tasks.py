"""
Nexus 后台任务（P5-05, P5-07）

包含：
- HeartbeatOfflineDetector: 后台心跳检测，标记离线 Agent
- SseDisconnectDetector: SSE 断连检测 + 自动降级到 Polling
- TaskTimeoutDetector: 任务超时检测和回收
- 降级恢复检测: Agent 重连 SSE 后自动切回 trigger_mode=sse
"""

import asyncio
from loguru import logger
import time
from datetime import datetime, timedelta
from typing import Dict, Set, Optional

from reins.common.config import TASK_TIMEOUT_MINUTES

from models import AgentStatus, TriggerMode

# 导入负载计算器
from reins.scheduler.load_calculator import update_agent_load

# 心跳超时阈值（秒）：超过此时长无心跳视为离线
HEARTBEAT_TIMEOUT_SECONDS = 30.0

# Agent 负载配置：离线时间阈值（分钟）
OFFLINE_REASSIGN_MINUTES = 5

# ============================================================================
# 全局探测器注册表（避免循环导入）
# ============================================================================

_detector_registry: Dict[str, "HeartbeatOfflineDetector | SseDisconnectDetector"] = {}

def register_detector(name: str, detector) -> None:
    """注册探测器实例（供 events.py 调用）"""
    global _detector_registry
    _detector_registry[name] = detector

def get_detector(name: str):
    """获取探测器实例"""
    return _detector_registry.get(name)

class HeartbeatOfflineDetector:
    """
    心跳离线检测（P5-05-03）

    后台定时任务，每 10 秒检测一次：
    - 检查 AgentRegistry 中所有 Agent 的 last_heartbeat
    - 超过 HEARTBEAT_TIMEOUT_SECONDS 未收到心跳 → 标记为 offline
    - 发布 agent_status_changed 事件到 EventBus
    """

    def __init__(self, agent_registry, event_bus_manager, db_manager=None, check_interval: float = 10.0):
        self._agent_registry = agent_registry
        self._event_bus = event_bus_manager
        self._db_manager = db_manager  # MAK-237: 用于任务重新分配
        self._check_interval = check_interval
        self._task: asyncio.Task = None
        self._running = False
        # 记录上次已标记离线的 agent（避免重复发布）
        self._known_offline: Set[str] = set()

    async def start(self):
        """启动后台检测"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info(f"[HeartbeatDetector] Started (interval={self._check_interval}s, timeout={HEARTBEAT_TIMEOUT_SECONDS}s)")

    async def stop(self):
        """停止后台检测"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[HeartbeatDetector] Stopped")

    async def _run(self):
        """检测循环"""
        while self._running:
            try:
                await self._check()
            except Exception as e:
                logger.error(f"[HeartbeatDetector] Check error: {e}")
            await asyncio.sleep(self._check_interval)

    async def _check(self):
        """执行一次检测"""
        now = datetime.now()
        dead_agents = []

        for agent in self._agent_registry.list_agents():
            elapsed = (now - agent.last_heartbeat).total_seconds()
            if elapsed > HEARTBEAT_TIMEOUT_SECONDS:
                if agent.status != AgentStatus.OFFLINE and agent.id not in self._known_offline:
                    dead_agents.append((agent.id, agent, elapsed))

        for agent_id, agent, elapsed in dead_agents:
            # 标记为 offline
            old_status = agent.status
            agent.status = AgentStatus.OFFLINE
            self._known_offline.add(agent_id)

            logger.info(f"[HeartbeatDetector] Agent {agent_id} marked OFFLINE (last heartbeat {elapsed:.1f}s ago)")

            # P5-05-04: 发布 agent_status_changed 事件
            try:
                from shared.eventbus.types import Event, EventPayload
                event = Event(
                    event_type="agent_status_changed",
                    agent_id=agent_id,
                    payload=EventPayload(
                        agent_id=agent_id,
                        from_status=old_status.value if hasattr(old_status, 'value') else str(old_status),
                        to_status="offline",
                    ),
                )
                self._event_bus.publish(event)
            except Exception as e:
                logger.warning(f"[HeartbeatDetector] Failed to publish event: {e}")

            # MAK-237: 离线超过 5 分钟后，重新分配任务
            if elapsed > OFFLINE_REASSIGN_MINUTES * 60:
                self._reassign_offline_agent_tasks(agent_id)

    def _reassign_offline_agent_tasks(self, agent_id: str):
        """重新分配 offline Agent 的任务（MAK-237）"""
        try:
            from sqlalchemy import text
            # 需要从 app 或 database manager 获取 connection
            # 这里假设已经可以通过某种方式获取 db connection
            # 实际实现中需要传入 db_manager
            
            logger.info(f"[HeartbeatDetector] Reassigning tasks for offline agent: {agent_id}")
            
            # 获取 database manager
            db_manager = getattr(self, '_db_manager', None)
            if not db_manager:
                logger.warning(f"[HeartbeatDetector] Cannot reassign tasks: no db_manager")
                return
            
            with db_manager.engine.begin() as conn:
                # 获取 Agent 的 pending 任务
                pending_query = text("""
                    SELECT id
                    FROM tasks
                    WHERE status IN ('todo', 'pending')
                      AND assigned_agent = :agent_id
                """)
                
                pending_tasks = conn.execute(pending_query, {"agent_id": agent_id}).fetchall()
                
                # 重新分配 pending 任务（清空 assigned_agent）
                if pending_tasks:
                    reassign_query = text("""
                        UPDATE tasks
                        SET assigned_agent = NULL,
                            updated_at = :now
                        WHERE status IN ('todo', 'pending')
                          AND assigned_agent = :agent_id
                    """)
                    
                    conn.execute(reassign_query, {
                        "agent_id": agent_id,
                        "now": datetime.utcnow(),
                    })
                    logger.info(f"[HeartbeatDetector] Reassigned {len(pending_tasks)} pending tasks for agent {agent_id}")
                
                # 标记 in_progress 任务为 blocked
                in_progress_query = text("""
                    UPDATE tasks
                    SET status = 'blocked',
                        blocked_reason = 'Agent went offline',
                        updated_at = :now
                    WHERE status = 'in_progress'
                      AND assigned_agent = :agent_id
                """)
                
                result = conn.execute(in_progress_query, {
                    "agent_id": agent_id,
                    "now": datetime.utcnow(),
                })
                
                if result.rowcount > 0:
                    logger.info(f"[HeartbeatDetector] Blocked {result.rowcount} in_progress tasks for agent {agent_id}")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"[HeartbeatDetector] Failed to reassign tasks for agent {agent_id}: {e}")

    def mark_online(self, agent_id: str):
        """当 Agent 发送心跳时调用，从已知离线集合中移除"""
        self._known_offline.discard(agent_id)

class SseDisconnectDetector:
    """
    SSE 断连检测 + 自动降级（P5-07-02, P5-07-03）

    后台定时任务，每 15 秒检测一次：
    - 检查 SSE 连接状态
    - 发现 SSE 断连（心跳超时）→ 自动将 Agent trigger_mode 切换为 polling
    - 发布 mode_switched 事件
    """

    def __init__(
        self,
        agent_registry,
        sse_adapter,
        event_bus_manager,
        db_manager,
        check_interval: float = 15.0,
        sse_heartbeat_timeout: float = 45.0,
    ):
        self._agent_registry = agent_registry
        self._sse_adapter = sse_adapter
        self._event_bus = event_bus_manager
        self._db_manager = db_manager
        self._check_interval = check_interval
        self._sse_heartbeat_timeout = sse_heartbeat_timeout
        self._task: asyncio.Task = None
        self._running = False
        # 记录已经降级的 agent（避免重复降级）
        self._degraded_agents: Set[str] = set()
        # SSE 在线连接追踪: agent_id → last_sse_activity
        self._sse_activity: Dict[str, float] = {}

    async def start(self):
        """启动断连检测"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info(f"[SseDisconnectDetector] Started (interval={self._check_interval}s, sse_timeout={self._sse_heartbeat_timeout}s)")

    async def stop(self):
        """停止断连检测"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[SseDisconnectDetector] Stopped")

    async def _run(self):
        """检测循环"""
        while self._running:
            try:
                await self._check()
            except Exception as e:
                logger.error(f"[SseDisconnectDetector] Check error: {e}")
            await asyncio.sleep(self._check_interval)

    async def _check(self):
        """执行一次检测"""
        now = time.time()

        # 获取当前 SSE 在线客户端
        try:
            sse_stats = self._sse_adapter.get_stats() if hasattr(self._sse_adapter, 'get_stats') else {}
            active_clients = sse_stats.get('active_clients', 0)
            clients = sse_stats.get('clients', [])
        except Exception as e:
            logger.warning(f"[SseDisconnectDetector] Failed to get SSE stats: {e}")
            clients = []

        # 更新活跃 agent 的 SSE 时间戳
        active_agent_ids = set()
        for client in clients:
            agent_id = client.get('agent_id')
            if agent_id:
                active_agent_ids.add(agent_id)
                self._sse_activity[agent_id] = now

        # 检测 SSE 断连：trigger_mode=sse 但无 SSE 活动的 agent
        for agent in self._agent_registry.list_agents():
            if agent.trigger_mode != TriggerMode.SSE:
                continue

            # 如果 trigger_mode=sse 但没有 SSE 活动记录
            if agent.id not in active_agent_ids:
                last_activity = self._sse_activity.get(agent_id, 0)
                elapsed = now - last_activity if last_activity else self._sse_heartbeat_timeout + 1

                if elapsed > self._sse_heartbeat_timeout and agent.id not in self._degraded_agents:
                    await self._degrade_to_polling(agent.id, agent)

    async def _degrade_to_polling(self, agent_id: str, agent):
        """触发降级：SSE → Polling"""
        old_mode = agent.trigger_mode
        agent.trigger_mode = TriggerMode.POLLING
        self._degraded_agents.add(agent_id)

        logger.info(f"[SseDisconnectDetector] Agent {agent_id} degraded: {old_mode} → polling")

        # 更新 DB 中的 trigger_mode
        try:
            from sqlalchemy import text
            with self._db_manager.engine.begin() as conn:
                conn.execute(
                    text("UPDATE agents SET trigger_mode='polling' WHERE id=:id"),
                    {"id": agent_id}
                )
        except Exception as e:
            logger.warning(f"[SseDisconnectDetector] DB update failed: {e}")

        # P5-07-04: 发布 mode_switched 事件
        try:
            from shared.eventbus.types import Event, EventPayload
            event = Event(
                event_type="mode_switched",
                agent_id=agent_id,
                payload=EventPayload(
                    agent_id=agent_id,
                    from_status=old_mode.value if hasattr(old_mode, 'value') else str(old_mode),
                    to_status="polling",
                    extra={"reason": "sse_disconnect", "degraded": True},
                ),
            )
            self._event_bus.publish(event)
        except Exception as e:
            logger.warning(f"[SseDisconnectDetector] Failed to publish mode_switched event: {e}")

    def on_sse_reconnect(self, agent_id: str):
        """
        P5-07-05: Agent 重连 SSE 时调用
        自动将 trigger_mode 切回 sse
        """
        if agent_id in self._degraded_agents:
            agent = self._agent_registry.get_agent(agent_id)
            if agent:
                old_mode = agent.trigger_mode
                agent.trigger_mode = TriggerMode.SSE
                self._degraded_agents.discard(agent_id)

                logger.info(f"[SseDisconnectDetector] Agent {agent_id} SSE recovered: {old_mode} → sse")

                # 更新 DB
                try:
                    from sqlalchemy import text
                    with self._db_manager.engine.begin() as conn:
                        conn.execute(
                            text("UPDATE agents SET trigger_mode='sse' WHERE id=:id"),
                            {"id": agent_id}
                        )
                except Exception as e:
                    logger.warning(f"[SseDisconnectDetector] DB update failed: {e}")

                # 发布 mode_switched 事件
                try:
                    from shared.eventbus.types import Event, EventPayload
                    event = Event(
                        event_type="mode_switched",
                        agent_id=agent_id,
                        payload=EventPayload(
                            agent_id=agent_id,
                            from_status=old_mode.value if hasattr(old_mode, 'value') else str(old_mode),
                            to_status="sse",
                            extra={"reason": "sse_recovered", "degraded": False},
                        ),
                    )
                    self._event_bus.publish(event)
                except Exception as e:
                    logger.warning(f"[SseDisconnectDetector] Failed to publish recovery event: {e}")

class TaskTimeoutDetector:
    """
    任务超时回收检测（P2）

    后台定时任务，定期扫描 in_progress 状态但超时的任务：
    - 默认每 5 分钟检测一次
    - 查找 started_at 超过 timeout_minutes 的 in_progress 任务
    - 将其标记为 timeout，并写 task_failure_log
    - 减少对应 agent 的 current_tasks 计数
    """

    def __init__(self, db_manager, check_interval: float = 300.0, timeout_minutes: int = None):
        self._db_manager = db_manager
        self._check_interval = check_interval  # 默认 5 分钟
        self._timeout_minutes = timeout_minutes if timeout_minutes is not None else TASK_TIMEOUT_MINUTES
        self._task: asyncio.Task = None
        self._running = False

    async def start(self):
        """启动后台检测"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info(
            f"[TaskTimeoutDetector] Started (interval={self._check_interval}s, "
            f"timeout={self._timeout_minutes}min)"
        )

    async def stop(self):
        """停止后台检测"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[TaskTimeoutDetector] Stopped")

    async def _run(self):
        """检测循环"""
        while self._running:
            try:
                await self._check()
            except Exception as e:
                logger.error(f"[TaskTimeoutDetector] Check error: {e}")
            await asyncio.sleep(self._check_interval)

    async def _check(self):
        """执行一次超时任务回收检测"""
        from datetime import timedelta
        from sqlalchemy import text
        import uuid

        cutoff = datetime.now() - timedelta(minutes=self._timeout_minutes)

        try:
            with self._db_manager.engine.begin() as conn:
                # 查找超时任务
                query = text("""
                    SELECT id, title, assigned_agent, started_at
                    FROM tasks
                    WHERE status = 'in_progress'
                      AND started_at IS NOT NULL
                      AND started_at < :cutoff
                """)
                timeout_tasks = conn.execute(query, {"cutoff": cutoff}).fetchall()

            if not timeout_tasks:
                return

            recovered = []
            for task in timeout_tasks:
                task_id = task.id
                agent_id = task.assigned_agent
                task_title = task.title

                # 1. 更新任务状态为 timeout
                with self._db_manager.engine.begin() as conn:
                    conn.execute(
                        text("""
                            UPDATE tasks
                            SET status = 'timeout',
                                updated_at = :now,
                                result_summary = '任务超时未完成，自动回收',
                                timeout_reason = :reason
                            WHERE id = :task_id
                        """),
                        {
                            "task_id": task_id,
                            "now": datetime.now(),
                            "reason": f"started_at超过{self._timeout_minutes}分钟未完成",
                        }
                    )

                    # 2. 写 task_failure_log
                    conn.execute(
                        text("""
                            INSERT INTO task_failure_log
                            (id, task_id, error_type, error_message, retry_count, max_retries, timestamp)
                            VALUES (:id, :task_id, :error_type, :error_message, 0, 0, :timestamp)
                        """),
                        {
                            "id": str(uuid.uuid4()),
                            "task_id": task_id,
                            "error_type": "timeout",
                            "error_message": f"任务超时未完成，自动回收（started_at={task.started_at}，超时阈值={self._timeout_minutes}分钟）",
                            "timestamp": datetime.now(),
                        }
                    )

                    # 3. 减少 agent 的 current_tasks 并重新计算 load
                    if agent_id:
                        conn.execute(
                            text("""
                                UPDATE agents
                                SET current_tasks = MAX(0, current_tasks - 1),
                                    updated_at = :now
                                WHERE id = :agent_id
                            """),
                            {
                                "agent_id": agent_id,
                                "now": datetime.now(),
                            }
                        )
                        
                        # 重新计算 load（通过 load_calculator 模块）
                        update_agent_load(conn, agent_id)

                recovered.append(task_id)
                logger.info(
                    f"[TaskTimeoutDetector] Recovered timeout task: {task_id} "
                    f"(title='{task_title}', agent={agent_id})"
                )

            if recovered:
                logger.info(
                    f"[TaskTimeoutDetector] Recovered {len(recovered)} timeout tasks: {recovered}"
                )

        except Exception as e:
            logger.error(f"[TaskTimeoutDetector] Recovery error: {e}")

    def trigger_recovery(self, timeout_minutes: int = None):
        """
        手动触发一次超时回收（供 API 调用）
        这是同步版本，用于 /internal/tasks/recover-timeout 端点
        """
        from datetime import timedelta
        from sqlalchemy import text
        import uuid

        timeout_minutes = timeout_minutes or self._timeout_minutes
        cutoff = datetime.now() - timedelta(minutes=timeout_minutes)

        try:
            with self._db_manager.engine.begin() as conn:
                query = text("""
                    SELECT id, title, assigned_agent, started_at
                    FROM tasks
                    WHERE status = 'in_progress'
                      AND started_at IS NOT NULL
                      AND started_at < :cutoff
                """)
                timeout_tasks = conn.execute(query, {"cutoff": cutoff}).fetchall()

            if not timeout_tasks:
                return {"recovered_count": 0, "task_ids": []}

            recovered = []
            for task in timeout_tasks:
                task_id = task.id
                agent_id = task.assigned_agent
                task_title = task.title

                # 1. 更新任务状态为 timeout
                with self._db_manager.engine.begin() as conn:
                    conn.execute(
                        text("""
                            UPDATE tasks
                            SET status = 'timeout',
                                updated_at = :now,
                                result_summary = '任务超时未完成，自动回收',
                                timeout_reason = :reason
                            WHERE id = :task_id
                        """),
                        {
                            "task_id": task_id,
                            "now": datetime.now(),
                            "reason": f"started_at超过{timeout_minutes}分钟未完成",
                        }
                    )

                    # 2. 写 task_failure_log
                    conn.execute(
                        text("""
                            INSERT INTO task_failure_log
                            (id, task_id, error_type, error_message, retry_count, max_retries, timestamp)
                            VALUES (:id, :task_id, :error_type, :error_message, 0, 0, :timestamp)
                        """),
                        {
                            "id": str(uuid.uuid4()),
                            "task_id": task_id,
                            "error_type": "timeout",
                            "error_message": f"任务超时未完成，自动回收（started_at={task.started_at}，超时阈值={timeout_minutes}分钟）",
                            "timestamp": datetime.now(),
                        }
                    )

                    # 3. 减少 agent 的 current_tasks 并重新计算 load
                    if agent_id:
                        conn.execute(
                            text("""
                                UPDATE agents
                                SET current_tasks = MAX(0, current_tasks - 1),
                                    updated_at = :now
                                WHERE id = :agent_id
                            """),
                            {
                                "agent_id": agent_id,
                                "now": datetime.now(),
                            }
                        )
                        
                        # 重新计算 load（通过 load_calculator 模块）
                        update_agent_load(conn, agent_id)

                recovered.append(task_id)
                logger.info(
                    f"[TaskTimeoutDetector] Manually recovered timeout task: {task_id} "
                    f"(title='{task_title}', agent={agent_id})"
                )

            return {"recovered_count": len(recovered), "task_ids": recovered}

        except Exception as e:
            logger.error(f"[TaskTimeoutDetector] Manual recovery error: {e}")
            raise
