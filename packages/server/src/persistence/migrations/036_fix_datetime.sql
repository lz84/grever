-- Migration 036: Fix datetime columns - text to integer timestamp
-- All datetime columns in tasks table were stored as ISO text strings
-- but the ORM model expects datetime objects. This caused SQLAlchemy
-- to fail when reading rows with malformed timestamps.

-- Convert created_at: 'YYYY-MM-DD HH:MM:SS.ffffff' -> Unix timestamp integer
UPDATE tasks SET created_at = (
    CAST((strftime('%s', substr(created_at, 1, 10) || ' ' || substr(created_at, 12, 8)) AS INTEGER)
    + CAST(substr(created_at, 21, 6) AS INTEGER) / 1000000.0
) WHERE typeof(created_at) = 'text' AND created_at LIKE '% %';

-- Convert updated_at (same format)
UPDATE tasks SET updated_at = (
    CAST((strftime('%s', substr(updated_at, 1, 10) || ' ' || substr(updated_at, 12, 8)) AS INTEGER)
    + CAST(substr(updated_at, 21, 6) AS INTEGER) / 1000000.0
) WHERE typeof(updated_at) = 'text' AND updated_at LIKE '% %';

-- Convert started_at (nullable, may be NULL or ISO text)
UPDATE tasks SET started_at = (
    CAST((strftime('%s', substr(started_at, 1, 10) || ' ' || substr(started_at, 12, 8)) AS INTEGER)
    + CAST(substr(started_at, 21, 6) AS INTEGER) / 1000000.0
) WHERE typeof(started_at) = 'text' AND started_at LIKE '% %';

-- Convert completed_at (nullable, may be NULL or ISO text)
UPDATE tasks SET completed_at = (
    CAST((strftime('%s', substr(completed_at, 1, 10) || ' ' || substr(completed_at, 12, 8)) AS INTEGER)
    + CAST(substr(completed_at, 21, 6) AS INTEGER) / 1000000.0
) WHERE typeof(completed_at) = 'text' AND completed_at LIKE '% %';

-- Verify: all should now be integer
SELECT 'created_at types:', typeof(created_at), 'count:', COUNT(*) FROM tasks GROUP BY typeof(created_at);
SELECT 'started_at types:', typeof(started_at), 'count:', COUNT(*) FROM tasks GROUP BY typeof(started_at);
