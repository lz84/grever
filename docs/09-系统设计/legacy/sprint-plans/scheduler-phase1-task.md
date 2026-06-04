# Phase 1: 调度器基础设施

> 完整设计见: `docs/scheduler-design.md`
> 这是 Phase 1，只做基础设施，不做调度逻辑

---

## 任务清单

### 1. 创建 scheduler 包结构

**新建文件**: `packages/server/src/reins/scheduler/__init__.py`

```python
"""
Nexus 调度引擎

Phase 1: 包结构 + 统计类 + 调度器占位
Phase 2+: 健康度管理 + 任务回收 + 任务分配 + 依赖解析
"""

from reins.scheduler.stats import SchedulerStats
from reins.scheduler.core import NexusScheduler

# 全局调度器实例（None 表示未启动）
_scheduler: NexusScheduler | None = None


def get_scheduler() -> NexusScheduler | None:
    """获取全局调度器实例"""
    return _scheduler


def set_scheduler(scheduler: NexusScheduler) -> None:
    """设置全局调度器实例"""
    global _scheduler
    _scheduler = scheduler


__all__ = ["NexusScheduler", "SchedulerStats", "get_scheduler", "set_scheduler"]
```

---

### 2. 创建 SchedulerStats 类

**新建文件**: `packages/server/src/reins/scheduler/stats.py`

```python
"""
调度统计

每 tick 更新一次，提供调度状态概览
"""

from datetime import datetime
from typing import Dict, Any


class SchedulerStats:
    """调度统计"""

    def __init__(self):
        self.total_ticks: int = 0
        self.last_tick_at: datetime | None = None

        # Agent 统计
        self.online_agents: int = 0
        self.stale_agents: int = 0
        self.offline_agents: int = 0

        # 任务统计
        self.total_tasks: int = 0
        self.todo_tasks: int = 0
        self.in_progress_tasks: int = 0
        self.done_tasks: int = 0
        self.blocked_tasks: int = 0
        self.timeout_tasks: int = 0

        # 本次 tick 动作统计
        self.assigned_this_tick: int = 0
        self.recovered_this_tick: int = 0
        self.unlocked_this_tick: int = 0

        # 累计统计
        self.total_assigned: int = 0
        self.total_recovered: int = 0
        self.total_unlocked: int = 0

    def update(self, step_results: dict) -> None:
        """从 step 结果更新统计"""
        self.total_ticks += 1
        self.last_tick_at = datetime.now()

        self.assigned_this_tick = step_results.get("assign", {}).get("assigned_count", 0)
        self.recovered_this_tick = step_results.get("recover", {}).get("recovered_count", 0)
        self.unlocked_this_tick = step_results.get("unlock", {}).get("unlocked_count", 0)

        self.total_assigned += self.assigned_this_tick
        self.total_recovered += self.recovered_this_tick
        self.total_unlocked += self.unlocked_this_tick

        # Agent 统计从 health step 获取
        health = step_results.get("health", {})
        self.online_agents = health.get("online_count", 0)
        self.stale_agents = health.get("stale_count", 0)
        self.offline_agents = health.get("offline_count", 0)

    def summary(self) -> str:
        """生成统计摘要字符串"""
        return (
            f"agents: {self.online_agents}online/{self.stale_agents}stale/{self.offline_agents}offline | "
            f"tasks: {self.todo_tasks}todo/{self.in_progress_tasks}progress/{self.done_tasks}done | "
            f"tick: assigned={self.assigned_this_tick} recovered={self.recovered_this_tick}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """转为 dict（给 API 使用）"""
        return {
            "total_ticks": self.total_ticks,
            "last_tick_at": self.last_tick_at.isoformat() if self.last_tick_at else None,
            "agents": {
                "online": self.online_agents,
                "stale": self.stale_agents,
                "offline": self.offline_agents,
            },
            "tasks": {
                "total": self.total_tasks,
                "todo": self.todo_tasks,
                "in_progress": self.in_progress_tasks,
                "done": self.done_tasks,
                "blocked": self.blocked_tasks,
                "timeout": self.timeout_tasks,
            },
            "this_tick": {
                "assigned": self.assigned_this_tick,
                "recovered": self.recovered_this_tick,
                "unlocked": self.unlocked_this_tick,
            },
            "total_actions": {
                "assigned": self.total_assigned,
                "recovered": self.total_recovered,
                "unlocked": self.total_unlocked,
            },
        }

    def refresh_task_stats(self, db_manager) -> None:
        """从 DB 刷新任务统计"""
        try:
            from sqlalchemy import text
            with db_manager.engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'todo' THEN 1 ELSE 0 END) as todo,
                        SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                        SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done,
                        SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked,
                        SUM(CASE WHEN status = 'timeout' THEN 1 ELSE 0 END) as timeout
                    FROM tasks
                """)).fetchone()
                if rows:
                    self.total_tasks = rows[0] or 0
                    self.todo_tasks = rows[1] or 0
                    self.in_progress_tasks = rows[2] or 0
                    self.done_tasks = rows[3] or 0
                    self.blocked_tasks = rows[4] or 0
                    self.timeout_tasks = rows[5] or 0
        except Exception:
            pass
```

---

### 3. 创建 NexusScheduler 核心（Phase 1 占位版）

**新建文件**: `packages/server/src/reins/scheduler/core.py`

```python
"""
Nexus 核心调度引擎

Phase 1: 启动/停止 + 空 tick 循环（仅刷新统计）
Phase 2+: 实现完整的调度逻辑
"""

import asyncio
import logging

from reins.scheduler.stats import SchedulerStats

logger = logging.getLogger(__name__)


class NexusScheduler:
    """
    Nexus 核心调度引擎

    职责（Phase 1 只实现启动/停止 + 统计）：
    - 统一管理 Agent 健康度
    - 主动分配/回收/重新分配任务
    - 监控任务超时
    - 解锁依赖关系
    - 生成调度报告
    """

    TICK_INTERVAL = 30  # 每 30 秒执行一次

    # 健康度阈值（秒）
    STALE_THRESHOLD = 300      # 5 分钟无心跳 → stale
    OFFLINE_THRESHOLD = 900    # 15 分钟无心跳 → offline

    # 任务超时（分钟）
    TASK_TIMEOUT = 30          # 30 分钟未完成 → timeout

    def __init__(self, db_manager):
        self.db = db_manager
        self.stats = SchedulerStats()
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
        """
        一次完整的调度周期

        Phase 1: 仅刷新统计
        Phase 2+: 实现完整的 7 步调度逻辑
        """
        step_results = {}

        # Phase 1: 仅刷新任务统计
        self.stats.refresh_task_stats(self.db)

        # 更新统计
        self.stats.update(step_results)

        # 每 10 个 tick 打印一次摘要
        if self.stats.total_ticks % 10 == 0:
            logger.info(f"[Scheduler] Tick {self.stats.total_ticks}: {self.stats.summary()}")
```

---

### 4. DB 迁移脚本

#### 4.1 迁移 014: Agent 健康度字段

**新建文件**: `packages/server/src/reins/persistence/migrations/014_agent_health.sql`

```sql
-- Phase 1: Agent 健康度字段

-- 新增健康度状态字段
ALTER TABLE agents ADD COLUMN health_status VARCHAR(20) DEFAULT 'online';
-- 值: online / stale / offline

-- 新增上次状态变更时间
ALTER TABLE agents ADD COLUMN last_status_change DATETIME;

-- 新增连续离线次数
ALTER TABLE agents ADD COLUMN consecutive_offline_count INTEGER DEFAULT 0;

-- 新增最大离线次数阈值
ALTER TABLE agents ADD COLUMN max_offline_before_deactivate INTEGER DEFAULT 5;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_agents_health_status ON agents(health_status);
CREATE INDEX IF NOT EXISTS idx_agents_last_heartbeat ON agents(last_heartbeat);
```

#### 4.2 迁移 015: Task 调度字段

**新建文件**: `packages/server/src/reins/persistence/migrations/015_task_scheduling.sql`

```sql
-- Phase 1: Task 调度扩展字段

-- 新增超时原因
ALTER TABLE tasks ADD COLUMN timeout_reason TEXT;

-- 新增已回收次数
ALTER TABLE tasks ADD COLUMN recovery_count INTEGER DEFAULT 0;

-- 新增调度优先级（动态调整）
ALTER TABLE tasks ADD COLUMN schedule_priority INTEGER DEFAULT 0;

-- 新增任务分配时间
ALTER TABLE tasks ADD COLUMN assigned_at DATETIME;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_agent ON tasks(assigned_agent) WHERE assigned_agent IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_unassigned ON tasks(status) WHERE status IN ('todo', 'pending');
CREATE INDEX IF NOT EXISTS idx_tasks_in_progress ON tasks(status, started_at) WHERE status = 'in_progress';
```

#### 4.3 迁移 016: 调度日志表

**新建文件**: `packages/server/src/reins/persistence/migrations/016_scheduler_log.sql`

```sql
-- Phase 1: 调度日志表

CREATE TABLE IF NOT EXISTS scheduler_log (
    id TEXT PRIMARY KEY,
    tick_number INTEGER,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    detail TEXT,
    success INTEGER DEFAULT 1,
    error TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_scheduler_log_action ON scheduler_log(action);
CREATE INDEX IF NOT EXISTS idx_scheduler_log_target ON scheduler_log(target_type, target_id);
```

---

### 5. server.py 集成

**修改文件**: `packages/server/src/reins/api/server.py`

#### 5.1 在 imports 区添加（文件顶部，其他 router import 附近）

```python
# Scheduler: 核心调度引擎
from reins.scheduler import NexusScheduler, set_scheduler
```

#### 5.2 在 _lifespan 函数的 startup 部分添加

找到 `await _task_timeout_detector.start()` 那一行后面，添加：

```python
        # Scheduler: 启动核心调度引擎
        try:
            from reins.database import get_db_manager
            db_mgr = get_db_manager()
            scheduler = NexusScheduler(db_manager=db_mgr)
            set_scheduler(scheduler)
            await scheduler.start()
            print("[Reins API] Scheduler initialized and started")
        except Exception as sched_err:
            print(f"[Reins API] Scheduler init warning: {sched_err}")
```

#### 5.3 在 shutdown 部分添加

在现有的 detector stop 代码后面添加：

```python
        # Scheduler: 停止调度引擎
        try:
            from reins.scheduler import get_scheduler
            sched = get_scheduler()
            if sched:
                await sched.stop()
                print("[Reins API] Scheduler stopped")
        except Exception as sched_err:
            print(f"[Reins API] Scheduler stop warning: {sched_err}")
```

#### 5.4 注册 DB 迁移执行（在现有的列迁移代码后面）

在现有的 `model_name` 列迁移后面（约第 320 行附近），添加：

```python
                # Scheduler Phase 1: 检查并执行调度器相关迁移
                migration_files = [
                    "014_agent_health",
                    "015_task_scheduling",
                    "016_scheduler_log",
                ]
                for mig_name in migration_files:
                    try:
                        mig_path = Path(__file__).parent.parent / "persistence" / "migrations" / f"{mig_name}.sql"
                        if mig_path.exists():
                            sql = mig_path.read_text(encoding="utf-8")
                            for stmt in sql.split(";"):
                                stmt = stmt.strip()
                                if stmt:
                                    conn_mig.execute(text(stmt))
                            conn_mig.commit()
                            print(f"[Reins API] Migration applied: {mig_name}")
                    except Exception as mig_e:
                        print(f"[Reins API] Migration skip {mig_name}: {mig_e}")
```

#### 5.5 新增调度状态查询 API

在文件末尾（其他 API 注册附近）添加：

```python
# ========== 调度器 API ==========

@app.get("/api/v1/scheduler/stats")
def get_scheduler_stats():
    """获取调度器统计"""
    from reins.scheduler import get_scheduler
    sched = get_scheduler()
    if not sched:
        raise HTTPException(503, "Scheduler not started")
    return sched.stats.to_dict()
```

---

## 验收标准

1. [ ] 新建 `reins/scheduler/` 包，包含 `__init__.py` / `stats.py` / `core.py`
2. [ ] 新建 3 个迁移文件（014/015/016），应用后 DB 新增列和表
3. [ ] server.py 启动时打印 `[Reins API] Scheduler started`
4. [ ] `GET /api/v1/scheduler/stats` 返回 200 + JSON
5. [ ] 调度器每 30 秒执行一次 tick（查看日志）
6. [ ] 服务关闭时打印 `[Reins API] Scheduler stopped`

## 注意事项

- Phase 1 的 tick 循环只做统计刷新，**不做任何 DB 写入操作**（除了 stats 刷新）
- 迁移脚本必须是幂等的（使用 `IF NOT EXISTS` 和 `ALTER TABLE ... ADD COLUMN` 前先检查）
- server.py 的修改要最小化，只在现有 lifespan 中插入启动/停止代码
- `get_db_manager()` 从 `reins.database` 导入
