-- Migration 033: HITL 审计字段
-- Sprint 90: human_input_requests 表新增审计字段
-- Date: 2026-05-24

ALTER TABLE human_input_requests ADD COLUMN required_role VARCHAR(50) DEFAULT NULL;
ALTER TABLE human_input_requests ADD COLUMN assigned_to VARCHAR(100) DEFAULT NULL;
ALTER TABLE human_input_requests ADD COLUMN approval_reason TEXT DEFAULT NULL;
ALTER TABLE human_input_requests ADD COLUMN before_snapshot TEXT DEFAULT NULL;
