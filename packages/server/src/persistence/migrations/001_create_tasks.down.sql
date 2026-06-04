-- Migration: 001_create_tasks (DOWN)
-- Rollback: Drop tasks table and indexes

DROP INDEX IF EXISTS idx_tasks_agent;
DROP INDEX IF NOT EXISTS idx_tasks_goal;
DROP INDEX IF NOT EXISTS idx_tasks_project;
DROP INDEX IF NOT EXISTS idx_tasks_status;
DROP TABLE IF EXISTS tasks;
