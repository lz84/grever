-- Migration: 026_add_depends_on_to_projects (DOWN)
-- Rollback: Remove depends_on column from projects table

-- SQLite doesn't support DROP COLUMN before 3.35.0, so we recreate the table
ALTER TABLE projects DROP COLUMN depends_on;
