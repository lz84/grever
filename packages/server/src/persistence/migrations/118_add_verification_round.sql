-- Migration: 117_add_verification_round
-- Description: Add verification_round column to tasks for multi-round negotiation tracking
-- Sprint 4 task-s4-2: 多轮协商 + 验证者选择

-- UP
ALTER TABLE tasks ADD COLUMN verification_round INTEGER NOT NULL DEFAULT 0;

-- DOWN
-- SQLite does not support DROP COLUMN directly in older versions
-- For rollback, we leave the column (safe since it defaults to 0)
