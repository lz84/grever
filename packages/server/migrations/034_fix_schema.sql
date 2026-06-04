-- Sprint 34: 数据库 schema 修复
-- 修复 Goal/Task 表缺失的列

-- Goals 表
ALTER TABLE goals ADD COLUMN IF NOT EXISTS due_date DATETIME;
ALTER TABLE goals ADD COLUMN IF NOT EXISTS failed_at DATETIME;
ALTER TABLE goals ADD COLUMN IF NOT EXISTS project_id INTEGER;

-- Tasks 表
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS due_date DATETIME;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS parent_id VARCHAR(32);

-- 创建 artifacts 表
CREATE TABLE IF NOT EXISTS artifacts (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36),
    project_id VARCHAR(36),
    goal_id VARCHAR(36),
    created_by VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) DEFAULT 'other',
    storage_path TEXT,
    url TEXT,
    size INTEGER DEFAULT 0,
    description TEXT,
    tags JSON,
    created_at DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(task_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_goal ON artifacts(goal_id);

-- 创建 task_dependencies 表
CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id VARCHAR(32) NOT NULL,
    dependency_id VARCHAR(32) NOT NULL,
    PRIMARY KEY (task_id, dependency_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (dependency_id) REFERENCES tasks(id)
);
