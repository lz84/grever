-- Rollback 033: 移除 HITL 审计字段

ALTER TABLE human_input_requests DROP COLUMN before_snapshot;
ALTER TABLE human_input_requests DROP COLUMN approval_reason;
ALTER TABLE human_input_requests DROP COLUMN assigned_to;
ALTER TABLE human_input_requests DROP COLUMN required_role;
