# Phase 2: 核心调度逻辑

> 完整设计见: `docs/scheduler-design.md`
> Phase 1 已完成：包结构 + 统计 + DB 迁移 + server.py 集成
> Phase 2: 实现 7 步调度循环的完整逻辑

---

## 任务清单

### 1. 新建 health_manager.py

**文件**: `packages/server/src/reins/scheduler/health_manager.py`

```python
"""
Agent 健康度管理器

职责：
1. 扫描所有 Agent 的 last_heartbeat
2. 根据时间阈值更新 health_status
3. 状态变更时触发相应动作
4. 更新 DB（持久化健康度）
"""

import logging
from datetime import datetime
from typing import List, Dict
from sqlalchemy import text

logger = logging.getLogger(__name__)


class AgentHealthManager:
    """Agent 健康度管理器"""

    STALE_THRESHOLD = 300       # 5 分钟无心跳 → stale
    OFFLINE_THRESHOLD = 900     # 15 分钟无心跳 → offline

    def __init__(self, db_manager):
        self.db = db_manager

    def scan(self) -> dict:
        """
        执行一次健康度扫描

        返回：
        {
            "online_count": int,
            "stale_count": int,
            "offline_count": int,
            "transitions": [{"agent_id": str, "from": str, "to": str}, ...],
            "changed": bool
        }
        """
        now = datetime.now()
        transitions = []
        online_count = 0
        stale_count = 0
        offline_count = 0

        try:
            with self.db.engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT id, name, status, health_status, last_heartbeat,
                           consecutive_offline_count
                    FROM agents
                """)).fetchall()

                for row in rows:
                    agent_id = row[0]
                    agent_name = row[1]
                    current_health = row[3] or "online"
                    last_heartbeat = row[4]
                    offline_count_val = row[5] or 0

                    # 计算距离上次心跳的秒数
                    if last_heartbeat:
                        try:
                            elapsed = (now - last_heartbeat).total_seconds()
                        except Exception:
                            elapsed = self.OFFLINE_THRESHOLD + 1
                    else:
                        elapsed = self.OFFLINE_THRESHOLD + 1

                    # 确定新的健康状态
                    if elapsed <= self.STALE_THRESHOLD:
                        new_health = "online"
                        online_count += 1
                    elif elapsed <= self.OFFLINE_THRESHOLD:
                        new_health = "stale"
                        stale_count += 1
                    else:
                        new_health = "offline"
                        offline_count += 1

                    # 状态变更时更新 DB
                    if new_health != current_health:
                        conn.execute(text("""
                            UPDATE agents
                            SET health_status = :new_health,
                                last_status_change = :now
                            WHERE id = :agent_id
                        """), {
                            "new_health": new_health,
                            "now": now,
                            "agent_id": agent_id,
                        })

                        transitions.append({
                            "agent_id": agent_id,
                            "agent_name": agent_name,
                            "from": current_health,
                            "to": new_health,
                        })

                        # 如果变 offline，记录离线次数
                        if new_health == "offline":
                            conn.execute(text("""
                                UPDATE agents
                                SET consecutive_offline_count = :count
                                WHERE id = :agent_id
                            """), {
                                "count": offline_count_val + 1,
                                "agent_id": agent_id,
                            })

                        # 如果恢复 online，重置离线次数
                        if new_health == "online" and current_health in ("stale", "offline"):
                            conn.execute(text("""
                                UPDATE agents
                                SET consecutive_offline_count = 0
                                WHERE id = :agent_id
                            """), {"agent_id": agent_id})

                        logger.info(
                            f"[HealthManager] Agent {agent_id} ({agent_name}): "
                            f"{current_health} → {new_health} (elapsed={elapsed:.0f}s)"
                        )

                conn.commit()

        except Exception as e:
            logger.error(f"[HealthManager] Scan error: {e}")

        return {
            "online_count": online_count,
            "stale_count": stale_count,
            "offline_count": offline_count,
            "transitions": transitions,
            "changed": len(transitions) > 0,
        }

    def on_heartbeat(self, agent_id: str):
        """
        Agent 发心跳时调用
        如果当前是 stale/offline → 恢复为 online
        """
        try:
            with self.db.engine.connect() as conn:
                row = conn.execute(text("""
                    SELECT health_status FROM agents WHERE id = :id
                """), {"id": agent_id}).fetchone()

                if not row:
                    return

                current = row[0] or "online"
                if current in ("stale", "offline"):
                    conn.execute(text("""
                        UPDATE agents
                        SET health_status = 'online',
                            last_status_change = :now,
                            consecutive_offline_count = 0
                        WHERE id = :id
                    """), {"now": datetime.now(), "id": agent_id})
                    conn.commit()
                    logger.info(f"[HealthManager] Agent {agent_id} recovered: {current} → online")
        except Exception as e:
            logger.error(f"[HealthManager] on_heartbeat error: {e}")

    def get_offline_agents(self) -> list[str]:
        """返回所有 offline Agent ID"""
        try:
            with self.db.engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT id FROM agents WHERE health_status = 'offline'
                """)).fetchall()
                return [r[0] for r in rows]
        except Exception:
            return []

    def get_stale_agents(self) -> list[str]:
        """返回所有 stale Agent ID"""
        try:
            with self.db.engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT id FROM agents WHERE health_status = 'stale'
                """)).fetchall()
                return [r[0] for r in rows]
        except Exception:
            return []
```

---

### 2. 新建 task_recoverer.py

**文件**: `packages/server/src/reins/scheduler/task_recoverer.py`

```python
"""
任务回收器

职责：
1. 回收 offline Agent 的任务
2. 回收超时的 in_progress 任务
3. 标记任务为 todo 状态（等待重新分配）
4. 记录回收原因
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import text

logger = logging.getLogger(__name__)


class TaskRecoverer:
    """任务回收器"""

    DEFAULT_TIMEOUT_MINUTES = 30

    def __init__(self, db_manager, timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES):
        self.db = db_manager
        self.timeout_minutes = timeout_minutes

    def recover_from_offline(self, agent_id: str) -> List[str]:
        """
        回收指定 offline Agent 的所有任务

        逻辑：
        1. 找到 assigned_agent = agent_id 且 status IN (todo, pending, in_progress) 的任务
        2. 更新 assigned_agent = NULL, status = todo, recovery_count += 1
        3. 写入 scheduler_log
        4. 减少 Agent 的 current_tasks

        返回：被回收的任务 ID 列表
        """
        try:
            with self.db.engine.connect() as conn:
                # 获取任务列表
                tasks = conn.execute(text("""
                    SELECT id, title FROM tasks
                    WHERE assigned_agent = :agent_id
                      AND status IN ('todo', 'pending', 'in_progress')
                """), {"agent_id": agent_id}).fetchall()

                if not tasks:
                    return []

                task_ids = [t[0] for t in tasks]

                # 更新任务状态
                conn.execute(text("""
                    UPDATE tasks
                    SET assigned_agent = NULL,
                        status = 'todo',
                        recovery_count = COALESCE(recovery_count, 0) + 1,
                        updated_at = :now
                    WHERE assigned_agent = :agent_id
                      AND status IN ('todo', 'pending', 'in_progress')
                """), {"agent_id": agent_id, "now": datetime.now()})

                # 减少 Agent 的 current_tasks
                conn.execute(text("""
                    UPDATE agents
                    SET current_tasks = MAX(0, current_tasks - :count),
                        updated_at = :now
                    WHERE id = :agent_id
                """), {"agent_id": agent_id, "count": len(tasks), "now": datetime.now()})

                # 写调度日志
                for task in tasks:
                    conn.execute(text("""
                        INSERT INTO scheduler_log (id, tick_number, action, target_type, target_id, detail, success, created_at)
                        VALUES (:id, 0, 'recover', 'task', :target_id, :detail, 1, :now)
                    """), {
                        "id": str(uuid.uuid4()),
                        "target_id": task[0],
                        "detail": f"Agent {agent_id} offline, task: {task[1]}",
                        "now": datetime.now(),
                    })

                conn.commit()
                logger.info(f"[TaskRecoverer] Recovered {len(tasks)} tasks from offline agent {agent_id}")
                return task_ids

        except Exception as e:
            logger.error(f"[TaskRecoverer] recover_from_offline error: {e}")
            return []

    def recover_from_timeout(self, timeout_minutes: int = None) -> List[str]:
        """
        回收所有超时的 in_progress 任务

        逻辑：
        1. 找到 status = in_progress AND started_at < (now - timeout_minutes) 的任务
        2. 更新 status = timeout, timeout_reason
        3. 减少 Agent 的 current_tasks
        4. 写调度日志

        返回：被回收的任务 ID 列表
        """
        tm = timeout_minutes or self.timeout_minutes
        cutoff = datetime.now() - timedelta(minutes=tm)

        try:
            with self.db.engine.connect() as conn:
                tasks = conn.execute(text("""
                    SELECT id, title, assigned_agent FROM tasks
                    WHERE status = 'in_progress'
                      AND started_at IS NOT NULL
                      AND started_at < :cutoff
                """), {"cutoff": cutoff}).fetchall()

                if not tasks:
                    return []

                task_ids = [t[0] for t in tasks]
                reason = f"执行超时（started_at < {cutoff.isoformat()}）"

                # 更新任务状态
                for task in tasks:
                    conn.execute(text("""
                        UPDATE tasks
                        SET status = 'timeout',
                            timeout_reason = :reason,
                            updated_at = :now
                        WHERE id = :task_id
                    """), {"reason": reason, "now": datetime.now(), "task_id": task[0]})

                    # 减少 Agent 的 current_tasks
                    if task[2]:
                        conn.execute(text("""
                            UPDATE agents
                            SET current_tasks = MAX(0, current_tasks - 1),
                                updated_at = :now
                            WHERE id = :agent_id
                        """), {"agent_id": task[2], "now": datetime.now()})

                    # 写调度日志
                    conn.execute(text("""
                        INSERT INTO scheduler_log (id, tick_number, action, target_type, target_id, detail, success, created_at)
                        VALUES (:id, 0, 'timeout', 'task', :target_id, :detail, 1, :now)
                    """), {
                        "id": str(uuid.uuid4()),
                        "target_id": task[0],
                        "detail": reason,
                        "now": datetime.now(),
                    })

                conn.commit()
                logger.info(f"[TaskRecoverer] Recovered {len(tasks)} timeout tasks")
                return task_ids

        except Exception as e:
            logger.error(f"[TaskRecoverer] recover_from_timeout error: {e}")
            return []

    def recover_single(self, task_id: str, reason: str) -> bool:
        """手动回收单个任务"""
        try:
            with self.db.engine.connect() as conn:
                row = conn.execute(text("""
                    SELECT assigned_agent, status FROM tasks WHERE id = :id
                """), {"id": task_id}).fetchone()

                if not row:
                    return False

                conn.execute(text("""
                    UPDATE tasks
                    SET assigned_agent = NULL,
                        status = 'todo',
                        recovery_count = COALESCE(recovery_count, 0) + 1,
                        updated_at = :now
                    WHERE id = :id
                """), {"now": datetime.now(), "id": task_id})

                if row[0]:
                    conn.execute(text("""
                        UPDATE agents
                        SET current_tasks = MAX(0, current_tasks - 1),
                            updated_at = :now
                        WHERE id = :agent_id
                    """), {"agent_id": row[0], "now": datetime.now()})

                conn.execute(text("""
                    INSERT INTO scheduler_log (id, tick_number, action, target_type, target_id, detail, success, created_at)
                    VALUES (:id, 0, 'recover', 'task', :target_id, :detail, 1, :now)
                """), {
                    "id": str(uuid.uuid4()),
                    "target_id": task_id,
                    "detail": reason,
                    "now": datetime.now(),
                })

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"[TaskRecoverer] recover_single error: {e}")
            return False
```

---

### 3. 新建 task_assigner.py

**文件**: `packages/server/src/reins/scheduler/task_assigner.py`

```python
"""
任务分配器

职责：
1. 从待分配队列中取任务
2. 按能力/负载匹配 Agent
3. 执行分配（写 DB）
4. 记录分配日志
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List
from sqlalchemy import text

logger = logging.getLogger(__name__)


class TaskAssigner:
    """任务分配器"""

    def __init__(self, db_manager):
        self.db = db_manager

    def assign_pending_tasks(self, max_per_tick: int = 10) -> dict:
        """
        分配待分配任务

        逻辑：
        1. 查询 status IN (todo, pending) AND assigned_agent IS NULL 的任务
        2. 按优先级排序
        3. 查询所有 online/stale Agent（排除 offline）
        4. 对每个任务匹配最低负载 Agent
        5. 分配并更新 DB

        返回：分配结果
        """
        try:
            with self.db.engine.connect() as conn:
                # 获取待分配任务
                pending_tasks = conn.execute(text("""
                    SELECT id, title, goal_id
                    FROM tasks
                    WHERE status IN ('todo', 'pending')
                      AND assigned_agent IS NULL
                    ORDER BY
                        CASE priority
                            WHEN 'critical' THEN 0
                            WHEN 'high' THEN 1
                            WHEN 'medium' THEN 2
                            WHEN 'low' THEN 3
                            ELSE 4
                        END,
                        created_at ASC
                    LIMIT :limit
                """), {"limit": max_per_tick}).fetchall()

                if not pending_tasks:
                    return {"assigned_count": 0, "assignments": [], "changed": False}

                # 获取可用 Agent（online 或 stale）
                agents = conn.execute(text("""
                    SELECT id, name, capabilities, load, current_tasks,
                           max_concurrent_tasks, load_threshold
                    FROM agents
                    WHERE health_status IN ('online', 'stale')
                      AND status = 'online'
                """)).fetchall()

                if not agents:
                    logger.warning("[TaskAssigner] No available agents for assignment")
                    return {"assigned_count": 0, "assignments": [], "changed": False}

                assignments = []

                for task in pending_tasks:
                    # 找负载最低的 Agent
                    best_agent = None
                    best_score = float('inf')

                    for agent in agents:
                        agent_id = agent[0]
                        current_tasks = agent[4] or 0
                        max_tasks = agent[5] or 5
                        load = agent[6] or 0

                        # 跳过已满的 Agent
                        if current_tasks >= max_tasks or load >= 80:
                            continue

                        score = (current_tasks or 0) * 10 + (load or 0)
                        if score < best_score:
                            best_score = score
                            best_agent = agent

                    if best_agent:
                        now = datetime.now()
                        conn.execute(text("""
                            UPDATE tasks
                            SET assigned_agent = :agent_id,
                                status = 'in_progress',
                                assigned_at = :now,
                                started_at = :now,
                                updated_at = :now
                            WHERE id = :task_id
                        """), {
                            "agent_id": best_agent[0],
                            "now": now,
                            "task_id": task[0],
                        })

                        # 增加 Agent current_tasks
                        conn.execute(text("""
                            UPDATE agents
                            SET current_tasks = COALESCE(current_tasks, 0) + 1,
                                load = :load,
                                updated_at = :now
                            WHERE id = :agent_id
                        """), {
                            "agent_id": best_agent[0],
                            "load": (best_agent[3] or 0) + 10,
                            "now": now,
                        })

                        # 写调度日志
                        conn.execute(text("""
                            INSERT INTO scheduler_log (id, tick_number, action, target_type, target_id, detail, success, created_at)
                            VALUES (:id, 0, 'assign', 'task', :target_id, :detail, 1, :now)
                        """), {
                            "id": str(uuid.uuid4()),
                            "target_id": task[0],
                            "detail": f"Assigned to {best_agent[0]} ({best_agent[1]})",
                            "now": now,
                        })

                        assignments.append({
                            "task_id": task[0],
                            "agent_id": best_agent[0],
                            "agent_name": best_agent[1],
                        })

                conn.commit()
                logger.info(f"[TaskAssigner] Assigned {len(assignments)} tasks")
                return {
                    "assigned_count": len(assignments),
                    "assignments": assignments,
                    "changed": len(assignments) > 0,
                }

        except Exception as e:
            logger.error(f"[TaskAssigner] assign_pending_tasks error: {e}")
            return {"assigned_count": 0, "assignments": [], "changed": False}

    def redistribute_recovered(self, max_per_tick: int = 5) -> dict:
        """
        重新分配被回收的任务

        与 assign_pending_tasks 的区别：
        - 专门处理 recovery_count > 0 的任务
        - 检查 retry_count < max_retries（超过则标记 failed）
        - 排除上次分配的 Agent
        """
        try:
            with self.db.engine.connect() as conn:
                # 获取被回收的任务（status = todo, recovery_count > 0, assigned_agent IS NULL）
                recovered_tasks = conn.execute(text("""
                    SELECT id, title, recovery_count, max_retries
                    FROM tasks
                    WHERE status = 'todo'
                      AND recovery_count > 0
                      AND assigned_agent IS NULL
                    ORDER BY recovery_count ASC, created_at ASC
                    LIMIT :limit
                """), {"limit": max_per_tick}).fetchall()

                if not recovered_tasks:
                    return {"assigned_count": 0, "assignments": [], "changed": False}

                # 获取可用 Agent
                agents = conn.execute(text("""
                    SELECT id, name, capabilities, load, current_tasks,
                           max_concurrent_tasks, load_threshold
                    FROM agents
                    WHERE health_status IN ('online', 'stale')
                      AND status = 'online'
                """)).fetchall()

                if not agents:
                    return {"assigned_count": 0, "assignments": [], "changed": False}

                assignments = []
                failed = []

                for task in recovered_tasks:
                    task_id = task[0]
                    task_title = task[1]
                    recovery_count = task[2] or 0
                    max_retries = task[3] or 3

                    # 超过最大重试次数 → 标记 failed
                    if recovery_count >= max_retries:
                        conn.execute(text("""
                            UPDATE tasks
                            SET status = 'failed',
                                error_type = 'max_retries_exceeded',
                                error_message = :msg,
                                updated_at = :now
                            WHERE id = :task_id
                        """), {
                            "msg": f"任务被回收 {recovery_count} 次，超过最大重试次数 {max_retries}",
                            "now": datetime.now(),
                            "task_id": task_id,
                        })
                        failed.append(task_id)
                        continue

                    # 找负载最低的 Agent
                    best_agent = None
                    best_score = float('inf')

                    for agent in agents:
                        current_tasks = agent[4] or 0
                        max_tasks = agent[5] or 5
                        load = agent[6] or 0

                        if current_tasks >= max_tasks or load >= 80:
                            continue

                        score = (current_tasks or 0) * 10 + (load or 0)
                        if score < best_score:
                            best_score = score
                            best_agent = agent

                    if best_agent:
                        now = datetime.now()
                        conn.execute(text("""
                            UPDATE tasks
                            SET assigned_agent = :agent_id,
                                status = 'in_progress',
                                assigned_at = :now,
                                started_at = :now,
                                updated_at = :now
                            WHERE id = :task_id
                        """), {
                            "agent_id": best_agent[0],
                            "now": now,
                            "task_id": task_id,
                        })

                        conn.execute(text("""
                            UPDATE agents
                            SET current_tasks = COALESCE(current_tasks, 0) + 1,
                                load = :load,
                                updated_at = :now
                            WHERE id = :agent_id
                        """), {
                            "agent_id": best_agent[0],
                            "load": (best_agent[3] or 0) + 10,
                            "now": now,
                        })

                        conn.execute(text("""
                            INSERT INTO scheduler_log (id, tick_number, action, target_type, target_id, detail, success, created_at)
                            VALUES (:id, 0, 'reassign', 'task', :target_id, :detail, 1, :now)
                        """), {
                            "id": str(uuid.uuid4()),
                            "target_id": task_id,
                            "detail": f"Reassigned to {best_agent[0]} (recovery #{recovery_count})",
                            "now": now,
                        })

                        assignments.append({
                            "task_id": task_id,
                            "agent_id": best_agent[0],
                            "agent_name": best_agent[1],
                        })

                if failed:
                    conn.execute(text("""
                        INSERT INTO scheduler_log (id, tick_number, action, target_type, target_id, detail, success, error, created_at)
                        VALUES (:id, 0, 'reassign', 'task', :target_id, :detail, 0, :error, :now)
                    """), {
                        "id": str(uuid.uuid4()),
                        "target_id": ",".join(failed),
                        "detail": "Max retries exceeded",
                        "error": f"Tasks exceeded max retries: {failed}",
                        "now": datetime.now(),
                    })

                conn.commit()
                logger.info(f"[TaskAssigner] Redistributed {len(assignments)} recovered tasks, {len(failed)} failed")
                return {
                    "assigned_count": len(assignments),
                    "assignments": assignments,
                    "failed": failed,
                    "changed": len(assignments) > 0 or len(failed) > 0,
                }

        except Exception as e:
            logger.error(f"[TaskAssigner] redistribute_recovered error: {e}")
            return {"assigned_count": 0, "assignments": [], "changed": False}
```

---

### 4. 更新 core.py（完整 7 步调度循环）

**修改文件**: `packages/server/src/reins/scheduler/core.py`

替换现有内容：

```python
"""
Nexus 核心调度引擎

Phase 1: 启动/停止 + 空 tick 循环
Phase 2: 完整 7 步调度逻辑
"""

import asyncio
import logging

from reins.scheduler.stats import SchedulerStats
from reins.scheduler.health_manager import AgentHealthManager
from reins.scheduler.task_recoverer import TaskRecoverer
from reins.scheduler.task_assigner import TaskAssigner

logger = logging.getLogger(__name__)


class NexusScheduler:
    """Nexus 核心调度引擎"""

    TICK_INTERVAL = 30  # 每 30 秒执行一次

    STALE_THRESHOLD = 300       # 5 分钟无心跳 → stale
    OFFLINE_THRESHOLD = 900     # 15 分钟无心跳 → offline
    TASK_TIMEOUT = 30           # 30 分钟未完成 → timeout

    def __init__(self, db_manager):
        self.db = db_manager
        self.stats = SchedulerStats()
        self.health_manager = AgentHealthManager(db_manager)
        self.recoverer = TaskRecoverer(db_manager, timeout_minutes=self.TASK_TIMEOUT)
        self.assigner = TaskAssigner(db_manager)
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        """启动调度循环（server.py 启动时调用）"""
        self._running = True
        self._task = asyncio.create_task(self._tick_loop())
        logger.info("[Scheduler] Started (interval=30s)")
        print("[Reins API] Scheduler started")

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
        print("[Reins API] Scheduler stopped")

    async def _tick_loop(self):
        """调度主循环"""
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"[Scheduler] Tick error: {e}")
            await asyncio.sleep(self.TICK_INTERVAL)

    async def _tick(self):
        """一次完整的调度周期"""
        step_results = {}

        # Step 1: Agent 健康度扫描
        step_results["health"] = self.health_manager.scan()

        # Step 2: 超时任务回收
        step_results["timeout"] = {
            "recovered_count": len(self.recoverer.recover_from_timeout()),
        }

        # Step 3: 离线 Agent 任务回收
        recover_count = 0
        for agent_id in self.health_manager.get_offline_agents():
            recovered = self.recoverer.recover_from_offline(agent_id)
            recover_count += len(recovered)
        step_results["recover"] = {"recovered_count": recover_count}

        # Step 4: 重新分配被回收任务
        step_results["reassign"] = self.assigner.redistribute_recovered()

        # Step 5: 分配待分配任务
        step_results["assign"] = self.assigner.assign_pending_tasks()

        # Step 6: 依赖解锁（Phase 3 实现，Phase 2 占位）
        step_results["unlock"] = {"unlocked_count": 0}

        # Step 7: 刷新任务统计
        self.stats.refresh_task_stats(self.db)
        self.stats.update(step_results)

        # 每 10 个 tick 打印一次摘要
        if self.stats.total_ticks % 10 == 0 and self.stats.total_ticks > 0:
            logger.info(f"[Scheduler] Tick {self.stats.total_ticks}: {self.stats.summary()}")
```

---

### 5. 更新 assignment.py 心跳集成

**修改文件**: `packages/server/src/reins/api/assignment.py`

找到 `agent_heartbeat_with_tasks` 函数（约第 317 行），在心跳成功后添加：

```python
# 通知调度器健康度管理器
try:
    from reins.scheduler import get_scheduler
    scheduler = get_scheduler()
    if scheduler:
        scheduler.health_manager.on_heartbeat(agent_id)
except Exception:
    pass  # 调度器未启动不影响心跳
```

具体位置：在 `reins.heartbeat_agent(agent_id, heartbeat_status if heartbeat_status else None)` 成功之后、返回之前。

---

## 验收标准

1. [ ] `health_manager.py` 创建完成，`scan()` 能扫描所有 Agent 并更新 health_status
2. [ ] `task_recoverer.py` 创建完成，能回收 offline Agent 任务和超时任务
3. [ ] `task_assigner.py` 创建完成，能按负载分配任务
4. [ ] `core.py` 更新为完整 7 步调度循环
5. [ ] `assignment.py` 心跳时调用 `health_manager.on_heartbeat()`
6. [ ] 调度器每 30 秒执行一次完整调度
7. [ ] `/api/v1/scheduler/stats` 显示分配/回收统计
8. [ ] 调度日志写入 scheduler_log 表
9. [ ] 服务启动/关闭正常

## 注意事项

- 每个 tick 步骤独立事务，一个步骤失败不影响其他步骤
- 任务分配时优先检查 Agent 负载（current_tasks < max_concurrent_tasks）
- 被回收任务重试次数超过 max_retries → 标记 failed
- Phase 6（依赖解锁）留空，Phase 3 实现
