-- Sprint 77: 迭代模式对话调整
-- 新建 goal_iterations 表，存储每次迭代的分析和讨论记录

CREATE TABLE IF NOT EXISTS goal_iterations (
    id TEXT PRIMARY KEY,
    goal_id TEXT NOT NULL,
    iteration_number INTEGER NOT NULL DEFAULT 1,
    solution_id TEXT,
    score REAL,
    status TEXT NOT NULL DEFAULT 'completed',  -- completed / planned / active
    ai_analysis TEXT,  -- AI 分析报告
    ai_discussion TEXT,  -- JSON 数组: [{role: 'human'/'ai', content: '...', timestamp: '...'}]
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY (goal_id) REFERENCES goals(id),
    FOREIGN KEY (solution_id) REFERENCES solutions(id)
);

CREATE INDEX IF NOT EXISTS idx_goal_iterations_goal_id ON goal_iterations(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_iterations_number ON goal_iterations(goal_id, iteration_number);
