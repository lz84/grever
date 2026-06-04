-- Migration 032 down: Remove executor_type column
-- Note: SQLite doesn't support DROP COLUMN directly in older versions,
-- but SQLite 3.35.0+ does. We use the modern approach.

ALTER TABLE tasks DROP COLUMN executor_type;
ALTER TABLE scenario_tasks DROP COLUMN executor_type;
