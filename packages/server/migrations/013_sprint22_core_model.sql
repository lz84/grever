-- Migration 013: Sprint 22 - 核心业务模型升级
-- 6 张表升级 + 4 张新表
-- 日期: 2026-04-17

-- ============================================================
-- 1. goals 表升级
-- ============================================================
ALTER TABLE goals ADD COLUMN IF NOT EXISTS matched_scenario_id VARCHAR(36);
ALTER TABLE goals ADD COLUMN IF NOT EXISTS workflow_id VARCHAR(36);
ALTER TABLE goals ADD COLUMN IF NOT EXISTS priority VARCHAR(10) DEFAULT 'P2';

-- ============================================================
-- 2. projects 表升级
-- ============================================================
ALTER TABLE projects ADD COLUMN IF NOT EXISTS workflow_id VARCHAR(36);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS phase_order INTEGER DEFAULT 0;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS matched_scenario_id VARCHAR(36);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS priority VARCHAR(10) DEFAULT 'P2';

-- ============================================================
-- 3. workflows 表升级
-- ============================================================
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS project_id VARCHAR(36);
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS parent_scenario_id VARCHAR(36);
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS level VARCHAR(20) DEFAULT 'project';

-- ============================================================
-- 4. tasks 表升级
-- ============================================================
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS workflow_step_id VARCHAR(36);

-- ============================================================
-- 5. scenarios 表升级
-- ============================================================
ALTER TABLE scenarios ADD COLUMN IF NOT EXISTS level VARCHAR(20) DEFAULT 'project';
ALTER TABLE scenarios ADD COLUMN IF NOT EXISTS template_dag TEXT;
ALTER TABLE scenarios ADD COLUMN IF NOT EXISTS agent_requirements TEXT;
ALTER TABLE scenarios ADD COLUMN IF NOT EXISTS trust_level VARCHAR(10) DEFAULT 'low';
ALTER TABLE scenarios ADD COLUMN IF NOT EXISTS source VARCHAR(30) DEFAULT 'manual';

-- ============================================================
-- 6. scenario_versions 新表
-- ============================================================
CREATE TABLE IF NOT EXISTS scenario_versions (
    id VARCHAR(36) PRIMARY KEY,
    scenario_id VARCHAR(36) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    template_dag TEXT,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_by VARCHAR(30) DEFAULT 'user',
    created_at DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (scenario_id) REFERENCES scenarios(id)
);
CREATE INDEX IF NOT EXISTS idx_scenario_versions_scenario ON scenario_versions(scenario_id);
CREATE INDEX IF NOT EXISTS idx_scenario_versions_active ON scenario_versions(scenario_id, is_active);

-- ============================================================
-- 7. agent_assignments 新表
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_assignments (
    id VARCHAR(36) PRIMARY KEY,
    goal_id VARCHAR(36),
    project_id VARCHAR(36),
    task_id VARCHAR(36),
    agent_id VARCHAR(36) NOT NULL,
    role VARCHAR(30) DEFAULT 'executor',
    status VARCHAR(20) DEFAULT 'assigned',
    created_at DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (goal_id) REFERENCES goals(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
CREATE INDEX IF NOT EXISTS idx_agent_assignments_goal ON agent_assignments(goal_id);
CREATE INDEX IF NOT EXISTS idx_agent_assignments_task ON agent_assignments(task_id);

-- ============================================================
-- 8. artifacts 新表
-- ============================================================
CREATE TABLE IF NOT EXISTS artifacts (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36),
    project_id VARCHAR(36),
    goal_id VARCHAR(36),
    created_by VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(30) DEFAULT 'other',
    storage_path TEXT NOT NULL,
    url TEXT,
    size INTEGER DEFAULT 0,
    description TEXT,
    tags TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (goal_id) REFERENCES goals(id)
);
CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(task_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_goal ON artifacts(goal_id);

-- ============================================================
-- 9. disputes 表升级（新增字段）
-- ============================================================
ALTER TABLE disputes ADD COLUMN IF NOT EXISTS raised_by_agent VARCHAR(36);
ALTER TABLE disputes ADD COLUMN IF NOT EXISTS discussion_log TEXT;
ALTER TABLE disputes ADD COLUMN IF NOT EXISTS deadline DATETIME;
