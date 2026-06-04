-- Migration 007: Create workflows and workflow_steps tables
-- Author: mazi
-- Date: 2026-04-10

-- UP Migration
CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    goal_id TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    name TEXT NOT NULL,
    description TEXT,
    dag TEXT,
    workflow_metadata TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workflows_goal_id ON workflows(goal_id);
CREATE INDEX IF NOT EXISTS idx_workflows_status_created ON workflows(status, created_at);

CREATE TABLE IF NOT EXISTS workflow_steps (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    dependencies TEXT,
    "order" INTEGER,
    agent_id TEXT,
    input_data TEXT,
    output_data TEXT,
    error TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    timeout_seconds INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_steps_workflow_id ON workflow_steps(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_steps_status ON workflow_steps(status);
CREATE INDEX IF NOT EXISTS idx_workflow_steps_workflow_order ON workflow_steps(workflow_id, "order");
