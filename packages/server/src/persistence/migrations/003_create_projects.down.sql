-- Migration: 003_create_projects (DOWN)
-- Rollback: Drop projects table and indexes

DROP INDEX IF EXISTS idx_projects_goal;
DROP INDEX IF NOT EXISTS idx_projects_status;
DROP TABLE IF EXISTS projects;
