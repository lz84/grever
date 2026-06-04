-- Sprint 22: 数据库表结构升级脚本
-- 执行时间：2026-04-17
-- 功能：为 Goal/Project/Workflow/Scenario/Task 表添加新字段

-- 1. Goals 表：添加 matched_scenario_id, workflow_id, priority 字段
ALTER TABLE goals ADD COLUMN matched_scenario_id VARCHAR(36);
ALTER TABLE goals ADD COLUMN workflow_id VARCHAR(36);
ALTER TABLE goals ADD COLUMN priority VARCHAR(20) DEFAULT 'medium';

-- 2. Projects 表：添加 workflow_id, phase_order, matched_scenario_id, priority 字段
ALTER TABLE projects ADD COLUMN workflow_id VARCHAR(36);
ALTER TABLE projects ADD COLUMN phase_order INTEGER;
ALTER TABLE projects ADD COLUMN matched_scenario_id VARCHAR(36);
ALTER TABLE projects ADD COLUMN priority VARCHAR(20) DEFAULT 'medium';

-- 3. Workflows 表：添加 project_id, parent_scenario_id, level 字段
ALTER TABLE workflows ADD COLUMN project_id VARCHAR(36);
ALTER TABLE workflows ADD COLUMN parent_scenario_id VARCHAR(36);
ALTER TABLE workflows ADD COLUMN level VARCHAR(20);

-- 4. Scenarios 表：添加 level, template_dag, agent_requirements, trust_level, source 字段
-- 注意：SQLite 不支持 JSON 类型，使用 TEXT 存储 JSON
ALTER TABLE scenarios ADD COLUMN level VARCHAR(20);
ALTER TABLE scenarios ADD COLUMN template_dag TEXT;
ALTER TABLE scenarios ADD COLUMN agent_requirements TEXT;
ALTER TABLE scenarios ADD COLUMN trust_level VARCHAR(20);
ALTER TABLE scenarios ADD COLUMN source VARCHAR(30);

-- 5. Tasks 表：添加 workflow_step_id 字段
ALTER TABLE tasks ADD COLUMN workflow_step_id VARCHAR(36);

-- 6. 创建 nuevos tables
-- 6.1 Agent Assignments 表
CREATE TABLE IF NOT EXISTS agent_assignments (
    id VARCHAR(36) PRIMARY KEY,
    goal_id VARCHAR(36),
    project_id VARCHAR(36),
    task_id VARCHAR(36),
    agent_id VARCHAR(36) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'executor',
    status VARCHAR(20) NOT NULL DEFAULT 'assigned',
    priority VARCHAR(20),
    assigned_at DATETIME,
    completed_at DATETIME,
    feedback TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (goal_id) REFERENCES goals(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_agent_assignments_goal_id ON agent_assignments(goal_id);
CREATE INDEX IF NOT EXISTS idx_agent_assignments_project_id ON agent_assignments(project_id);
CREATE INDEX IF NOT EXISTS idx_agent_assignments_task_id ON agent_assignments(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_assignments_agent_id ON agent_assignments(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_assignments_status ON agent_assignments(status);

-- create indexes for workflows table
CREATE INDEX IF NOT EXISTS idx_workflows_project_id ON workflows(project_id);
CREATE INDEX IF NOT EXISTS idx_workflows_parent_scenario_id ON workflows(parent_scenario_id);
