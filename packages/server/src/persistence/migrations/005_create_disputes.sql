-- Migration: 005_create_disputes
-- Description: 创建 disputes 表
-- Author: kouzi
-- Date: 2026-04-08

-- UP Migration
CREATE TABLE IF NOT EXISTS disputes (
    id TEXT PRIMARY KEY,
    dispute_type TEXT NOT NULL,
    description TEXT,
    involved_agents TEXT,
    related_task_id TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    resolution TEXT,
    resolved_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_disputes_status ON disputes(status);
CREATE INDEX IF NOT EXISTS idx_disputes_type ON disputes(dispute_type);
