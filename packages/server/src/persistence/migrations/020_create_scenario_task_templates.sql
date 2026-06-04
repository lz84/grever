-- Migration 020: Create scenario_task_templates table
-- Author: Kouzi
-- Date: 2026-05-01
-- Task: Task 5 - 自定义场景创建 API（三层结构）

-- UP Migration
CREATE TABLE IF NOT EXISTS scenario_task_templates (
    id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    phase_name TEXT NOT NULL,
    task_name TEXT NOT NULL,
    task_description TEXT,
    agent_type TEXT,
    required_capabilities TEXT,  -- JSON array as text
    dependencies TEXT,  -- JSON array of template ids as text
    order_in_phase INTEGER NOT NULL DEFAULT 0,
    estimated_hours REAL DEFAULT 0.0,
    priority TEXT DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scenario_task_templates_scenario_id ON scenario_task_templates(scenario_id);
CREATE INDEX IF NOT EXISTS idx_scenario_task_templates_phase ON scenario_task_templates(phase_name);
CREATE INDEX IF NOT EXISTS idx_scenario_task_templates_order ON scenario_task_templates(order_in_phase);

-- DOWN Migration (would be in separate file)
-- DROP TABLE IF EXISTS scenario_task_templates;