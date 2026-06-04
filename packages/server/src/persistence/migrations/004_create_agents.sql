-- Migration: 004_create_agents
-- Description: 创建 agents 表
-- Author: kouzi
-- Date: 2026-04-08

-- UP Migration
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    capabilities TEXT,
    status TEXT NOT NULL DEFAULT 'offline',
    address TEXT,
    metadata TEXT,
    load INTEGER NOT NULL DEFAULT 0,
    current_tasks INTEGER NOT NULL DEFAULT 0,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_capabilities ON agents(capabilities);
