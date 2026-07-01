-- Migration 119: Add main_agent_id to goals
-- Purpose: Store the primary/main agent assigned to execute this goal
ALTER TABLE goals ADD COLUMN main_agent_id VARCHAR(32) DEFAULT NULL;
