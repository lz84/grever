-- Migration 088: E-1~E-4 评估分解字段
-- 新增 goals 表字段：decomposition_mode, decomposition_status, coordinator_agent_id, default_decomposition_used

-- goals.decomposition_mode: 分解模式 (auto|manual|hitl)
ALTER TABLE goals ADD COLUMN decomposition_mode TEXT DEFAULT 'auto';

-- goals.decomposition_status: 分解状态 (pending|in_progress|confirmed|abandoned)
ALTER TABLE goals ADD COLUMN decomposition_status TEXT DEFAULT 'pending';

-- goals.coordinator_agent_id: 负责协调分解的 Agent ID
ALTER TABLE goals ADD COLUMN coordinator_agent_id TEXT;

-- goals.default_decomposition_used: 是否使用了默认分解 (0=否, 1=是)
ALTER TABLE goals ADD COLUMN default_decomposition_used INTEGER DEFAULT 0;
