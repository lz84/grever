-- Migration: 004_create_agents (DOWN)
-- Rollback: Drop agents table and indexes

DROP INDEX IF EXISTS idx_agents_capabilities;
DROP INDEX IF NOT EXISTS idx_agents_status;
DROP TABLE IF EXISTS agents;
