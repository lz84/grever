-- Migration: 003_create_projects
-- Description: 创建 projects 表
-- Author: kouzi
-- Date: 2026-04-08

-- UP Migration
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    goal_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    members TEXT,
    task_ids TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_goal ON projects(goal_id);
