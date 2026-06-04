-- Migration 032: Add executor_type column for HITL support
-- Date: 2026-05-24
-- Sprint 89: 数据底座 + 实例化链路

ALTER TABLE tasks ADD COLUMN executor_type VARCHAR(20) DEFAULT 'ai';
ALTER TABLE scenario_tasks ADD COLUMN executor_type VARCHAR(20) DEFAULT 'ai';
