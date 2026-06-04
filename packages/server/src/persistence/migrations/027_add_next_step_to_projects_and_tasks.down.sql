-- Migration 027 down: Remove next_step column
-- SQLite does not support DROP COLUMN in older versions; use ALTER TABLE DROP COLUMN for 3.35.0+

ALTER TABLE projects DROP COLUMN IF EXISTS next_step;
ALTER TABLE tasks DROP COLUMN IF EXISTS next_step;
