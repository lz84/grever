-- Phase 1: 调度日志表

CREATE TABLE IF NOT EXISTS scheduler_log (
    id TEXT PRIMARY KEY,
    tick_number INTEGER,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    detail TEXT,
    success INTEGER DEFAULT 1,
    error TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_scheduler_log_action ON scheduler_log(action);
CREATE INDEX IF NOT EXISTS idx_scheduler_log_target ON scheduler_log(target_type, target_id);
