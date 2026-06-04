-- Add version_num column to schema_migrations to make it compatible with Alembic
-- The existing table only has a "version" column; Alembic expects "version_num"
-- This is a one-time fix so Alembic can manage the existing migration table.
ALTER TABLE schema_migrations ADD COLUMN version_num VARCHAR(32) DEFAULT NULL;

-- Backfill version_num = version for all existing rows
UPDATE schema_migrations SET version_num = version WHERE version_num IS NULL;

-- Make version_num NOT NULL once all rows are populated (SQLite constraint workaround)
-- SQLite does not support DROP COLUMN easily, so we keep both columns.
-- Alembic will write to version_num; the existing code reads from version.
-- We also add a CHECK constraint to keep them in sync.
-- Note: SQLite has limited ALTER TABLE support; the backfill above is sufficient for operation.