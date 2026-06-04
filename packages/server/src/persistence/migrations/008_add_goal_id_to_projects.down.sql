-- Migration: 008_add_goal_id_to_projects (DOWN)
-- Rollback: 移除 projects 表的 goal_id 字段

DROP INDEX IF EXISTS idx_projects_goal;
ALTER TABLE projects DROP COLUMN goal_id;
