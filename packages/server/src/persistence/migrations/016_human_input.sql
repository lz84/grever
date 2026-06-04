-- Migration 016: Add human_input_requests table and waiting_human status support

-- Create human_input_requests table if it doesn't exist
CREATE TABLE IF NOT EXISTS human_input_requests (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    input_type TEXT DEFAULT 'confirmation',
    status TEXT DEFAULT 'pending',
    input_data TEXT,
    submitted_by TEXT,
    submitted_at TEXT,
    rejected_reason TEXT,
    context TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_human_input_task ON human_input_requests(task_id);
CREATE INDEX IF NOT EXISTS idx_human_input_status ON human_input_requests(status);
CREATE INDEX IF NOT EXISTS idx_human_input_submitted ON human_input_requests(submitted_at);

-- Note: SQLite doesn't support adding values to CHECK constraints directly,
-- but we ensure the waiting_human status is supported by application logic
-- The TaskStatus enum in the Python code handles this

-- Migration completed