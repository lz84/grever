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
