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
