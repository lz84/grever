-- Migration 016: Verification cycle columns + task_comments enhancements
-- Sprint 54: Verifier-Executor communication mechanism

-- 1. Add verification_cycle to tasks
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS verification_cycle INT DEFAULT 0;

-- 2. Add ruling_comment_id and instruction_comment_id for re-dispatch
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ruling_comment_id TEXT NULL;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS instruction_comment_id TEXT NULL;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS ruling_instruction TEXT NULL;

-- 3. Verify task_comments table exists (should already exist from Sprint 42)
-- If it doesn't exist, create it
CREATE TABLE IF NOT EXISTS task_comments (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    author TEXT NOT NULL,
    author_role TEXT DEFAULT 'agent',
    type TEXT DEFAULT 'comment',
    content TEXT NOT NULL,
    is_agent_reply INT DEFAULT 0,
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE INDEX IF NOT EXISTS idx_task_comments_task_id ON task_comments(task_id);
CREATE INDEX IF NOT EXISTS idx_task_comments_type ON task_comments(type);
