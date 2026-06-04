-- Migration 027: Add next_step column to projects and tasks
-- Purpose: Forward-link for DAG drawing (derived from depends_on)
-- Date: 2026-05-18
-- Does NOT remove depends_on (backward compatible)

ALTER TABLE projects ADD COLUMN next_step TEXT DEFAULT '[]';
ALTER TABLE tasks    ADD COLUMN next_step TEXT DEFAULT '[]';
