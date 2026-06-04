-- Scenario Task Templates 表迁移脚本
-- 执行时间：2026-05-02
-- 功能：创建场景任务模板表，用于存储场景中的标准化任务定义

-- 创建场景任务模板表
CREATE TABLE IF NOT EXISTS scenario_task_templates (
    id VARCHAR(36) PRIMARY KEY,
    scenario_id VARCHAR(36) NOT NULL,
    phase_name VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    agent_requirements TEXT,
    priority VARCHAR(20) DEFAULT 'medium',
    estimated_hours FLOAT,
    "order" INTEGER,
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (scenario_id) REFERENCES scenarios(id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_scenario_task_templates_scenario_id ON scenario_task_templates(scenario_id);
CREATE INDEX IF NOT EXISTS idx_scenario_task_templates_phase_name ON scenario_task_templates(phase_name);
CREATE INDEX IF NOT EXISTS idx_scenario_task_templates_priority ON scenario_task_templates(priority);
