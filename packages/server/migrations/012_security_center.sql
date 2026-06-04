-- MAK-192: 安全中心数据库迁移
-- 创建 audit_logs 和 alerts 表

-- 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    operation VARCHAR(50) NOT NULL,  -- create, update, delete, access
    resource_type VARCHAR(50) NOT NULL,  -- goal, project, task, agent, etc.
    resource_id VARCHAR(36) NOT NULL,
    operator VARCHAR(32) NOT NULL,  -- user/agent ID
    details JSON,
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    created_at DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_operator ON audit_logs(operator);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);

-- 告警表
CREATE TABLE IF NOT EXISTS alerts (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    level VARCHAR(20) NOT NULL DEFAULT 'warning',  -- critical, warning, info
    category VARCHAR(50) NOT NULL,  -- security, performance, business, system
    status VARCHAR(20) NOT NULL DEFAULT 'open',  -- open, acknowledged, resolved, closed
    source VARCHAR(100),  -- alert source: monitoring, manual, automated
    related_resource_type VARCHAR(50),
    related_resource_id VARCHAR(36),
    resolved_by VARCHAR(32),
    resolved_at DATETIME,
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX idx_alerts_level ON alerts(level);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_category ON alerts(category);
CREATE INDEX idx_alerts_created ON alerts(created_at);
CREATE INDEX idx_alerts_resource ON alerts(related_resource_type, related_resource_id);
