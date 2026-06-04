-- Migration 040: A2A Messages, Trust Evaluations, and Roles Tables
-- Date: 2026-06-02

-- A2A 消息表
CREATE TABLE IF NOT EXISTS a2a_messages (
    id TEXT PRIMARY KEY,
    broadcast_id TEXT,
    source_agent_id TEXT NOT NULL,
    target_agent_id TEXT NOT NULL,
    message TEXT NOT NULL,
    channel TEXT DEFAULT 'default',
    priority TEXT DEFAULT 'normal',
    status TEXT DEFAULT 'pending',
    metadata TEXT,
    requires_ack INTEGER DEFAULT 0,
    ack_status TEXT,
    ack_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP,
    ack_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_a2a_source ON a2a_messages(source_agent_id);
CREATE INDEX IF NOT EXISTS idx_a2a_target ON a2a_messages(target_agent_id);
CREATE INDEX IF NOT EXISTS idx_a2a_status ON a2a_messages(status);
CREATE INDEX IF NOT EXISTS idx_a2a_broadcast ON a2a_messages(broadcast_id);
CREATE INDEX IF NOT EXISTS idx_a2a_created ON a2a_messages(created_at);

-- 信任评估记录表
CREATE TABLE IF NOT EXISTS trust_evaluations (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    score REAL NOT NULL,
    level TEXT NOT NULL,
    reason TEXT,
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trust_agent ON trust_evaluations(agent_id);
CREATE INDEX IF NOT EXISTS idx_trust_created ON trust_evaluations(created_at);

-- RBAC 角色表
CREATE TABLE IF NOT EXISTS roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    permissions TEXT DEFAULT '[]',
    level INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_roles_status ON roles(status);
CREATE INDEX IF NOT EXISTS idx_roles_level ON roles(level);
