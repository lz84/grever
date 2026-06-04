-- Migration: 002_create_goals (DOWN)
-- Rollback: Drop goals table and indexes

DROP INDEX IF EXISTS idx_goals_parent;
DROP INDEX IF NOT EXISTS idx_goals_status;
DROP TABLE IF EXISTS goals;
