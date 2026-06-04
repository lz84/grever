-- Phase 1: Agent 健康度字段
-- 各字段添加语句分别执行（SQLite 不支持一次 ALTER TABLE 添加多个列）

-- 新增健康度状态字段
ALTER TABLE agents ADD COLUMN health_status VARCHAR(20) DEFAULT 'online';

-- 新增上次状态变更时间
ALTER TABLE agents ADD COLUMN last_status_change DATETIME;

-- 新增连续离线次数
ALTER TABLE agents ADD COLUMN consecutive_offline_count INTEGER DEFAULT 0;

-- 新增最大离线次数阈值
ALTER TABLE agents ADD COLUMN max_offline_before_deactivate INTEGER DEFAULT 5;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_agents_health_status ON agents(health_status);
CREATE INDEX IF NOT EXISTS idx_agents_last_heartbeat ON agents(last_heartbeat);
