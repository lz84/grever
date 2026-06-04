-- Migration 030: 创建 system_config 表（统一系统配置存储）
-- 包含 agent 主动探测等系统参数

CREATE TABLE IF NOT EXISTS system_config (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TEXT,
    updated_by TEXT,
    UNIQUE(category, key)
);
