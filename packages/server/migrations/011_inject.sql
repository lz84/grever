-- MAK-190: 注入管理数据库迁移
-- 创建注入规则和日志表

-- 注入规则表
CREATE TABLE IF NOT EXISTS grasp_inject_rules (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    trigger_condition VARCHAR(500) NOT NULL,
    target_kb VARCHAR(100) NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now'))
);

-- 注入日志表
CREATE TABLE IF NOT EXISTS grasp_inject_logs (
    id VARCHAR(36) PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    type VARCHAR(50) NOT NULL,
    cognition_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'success',
    error_message TEXT,
    extra JSON,
    created_at DATETIME DEFAULT (datetime('now'))
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_grasp_inject_source ON grasp_inject_logs(source);
CREATE INDEX IF NOT EXISTS idx_grasp_inject_type ON grasp_inject_logs(type);
CREATE INDEX IF NOT EXISTS idx_grasp_inject_status ON grasp_inject_logs(status);
