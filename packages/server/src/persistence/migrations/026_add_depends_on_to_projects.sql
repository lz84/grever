-- Migration: 026_add_depends_on_to_projects
-- Description: Add depends_on TEXT column to projects table (stores JSON array)
-- Date: 2026-05-18

ALTER TABLE projects ADD COLUMN depends_on TEXT;
