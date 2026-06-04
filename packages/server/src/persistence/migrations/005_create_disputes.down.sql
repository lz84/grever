-- Migration: 005_create_disputes (DOWN)
-- Rollback: Drop disputes table and indexes

DROP INDEX IF EXISTS idx_disputes_type;
DROP INDEX IF NOT EXISTS idx_disputes_status;
DROP TABLE IF EXISTS disputes;
