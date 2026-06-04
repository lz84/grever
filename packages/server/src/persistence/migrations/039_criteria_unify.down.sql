-- Rollback 039: 移除 done_criteria 列
ALTER TABLE tasks DROP COLUMN done_criteria;
