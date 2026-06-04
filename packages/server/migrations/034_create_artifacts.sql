-- Sprint 34: 创建 artifacts 成果物表
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
