-- Sprint 77: P1-6 复合索引
-- Date: 2026-05-13
-- Author: 刚子
-- 安全：仅添加索引，不修改表结构，不影响数据

-- (project_id, status) — 任务列表查询：SELECT * FROM tasks WHERE project_id=? AND status=?
CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON tasks(project_id, status);

-- (assigned_agent, status) — 心跳返回 pending tasks
CREATE INDEX IF NOT EXISTS idx_tasks_agent_status ON tasks(assigned_agent, status);

-- (goal_id, round) — 方案查询
CREATE INDEX IF NOT EXISTS idx_solutions_goal_round ON solutions(goal_id, round);

-- (agent_id, timestamp) — 心跳日志查询
CREATE INDEX IF NOT EXISTS idx_heartbeat_logs_agent_timestamp ON heartbeat_logs(agent_id, timestamp);

-- (task_id, created_at) — 执行日志查询
CREATE INDEX IF NOT EXISTS idx_execution_logs_task_created ON execution_logs(task_id, created_at);

-- ============================================================
-- P1-7: 外键约束（Phase 2 Alembic 统一处理）
-- 这里仅启用 SQLite 外键检查，不重建表
-- ============================================================
PRAGMA foreign_keys = ON;
