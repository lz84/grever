-- Migration 028: Capability Tag System Phase 1
-- 2026-05-18: DB schema changes for unified capability_tags

-- 1. Agent 表：重命名 capabilities 为 capability_tags
ALTER TABLE agents RENAME COLUMN capabilities TO capability_tags;

-- 2. Goal 表：新增 capability_tags
ALTER TABLE goals ADD COLUMN capability_tags TEXT DEFAULT '{}';

-- 3. Project 表：新增 capability_tags
ALTER TABLE projects ADD COLUMN capability_tags TEXT DEFAULT '{}';

-- 4. Task 表：新增 capability_tags + 删除 category
ALTER TABLE tasks ADD COLUMN capability_tags TEXT DEFAULT '{}';
ALTER TABLE tasks DROP COLUMN category;

-- 5. Scenario 表：新增 fullset 字段
ALTER TABLE scenarios ADD COLUMN fullset TEXT DEFAULT '{}';

-- 6. human_input_requests 表：扩展支持 Goal/Project 级 HITL
ALTER TABLE human_input_requests ADD COLUMN goal_id TEXT;
ALTER TABLE human_input_requests ADD COLUMN project_id TEXT;
ALTER TABLE human_input_requests ADD COLUMN scenario_ref TEXT;
ALTER TABLE human_input_requests ADD COLUMN default_value TEXT;
ALTER TABLE human_input_requests ADD COLUMN timeout_action TEXT;
ALTER TABLE human_input_requests ADD COLUMN timeout_minutes INTEGER;
ALTER TABLE human_input_requests ADD COLUMN branches TEXT;
ALTER TABLE human_input_requests ADD COLUMN response TEXT;
ALTER TABLE human_input_requests ADD COLUMN responder_id TEXT;

-- 7. 权重存储表
CREATE TABLE IF NOT EXISTS agent_tag_weights (
    agent_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    last_observed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (agent_id, tag)
);
