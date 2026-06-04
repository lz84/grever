-- Migration: 006_schema_migrations
-- Description: 创建 schema_migrations 表（版本追踪）
-- Author: kouzi
-- Date: 2026-04-08

-- UP Migration
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rolled_back_at TIMESTAMP,
    direction TEXT DEFAULT 'up'
);
