-- Migration: Add verifier_agent_id column to goals, projects, and tasks tables
-- Author: Kouzi
-- Description: Adds support for three-level verifier agent inheritance chain

-- Check if columns exist before adding them
-- For SQLite, we'll add them directly since it doesn't support IF NOT EXISTS for columns

-- Add verifier_agent_id to goals table
ALTER TABLE goals ADD COLUMN verifier_agent_id TEXT NULL;

-- Add verifier_agent_id to projects table
ALTER TABLE projects ADD COLUMN verifier_agent_id TEXT NULL;

-- Add verifier_agent_id to tasks table
ALTER TABLE tasks ADD COLUMN verifier_agent_id TEXT NULL;

-- Update schema version if applicable
UPDATE schema_versions SET version = '015' WHERE component = 'reins';
-- If schema_versions doesn't exist or doesn't have reins entry, this might fail safely