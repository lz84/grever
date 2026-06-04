-- Sprint 64: 能力库表
-- 存储 Agent 能力的元数据（名称/分类/描述/状态/使用统计）

CREATE TABLE IF NOT EXISTS capabilities (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL DEFAULT 'other',
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    agents TEXT NOT NULL DEFAULT '[]',
    usage_count INTEGER NOT NULL DEFAULT 0,
    last_used DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_capabilities_name ON capabilities(name);
CREATE INDEX IF NOT EXISTS idx_capabilities_category ON capabilities(category);
CREATE INDEX IF NOT EXISTS idx_capabilities_status ON capabilities(status);
