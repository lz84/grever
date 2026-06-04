-- Rollback 031: 移除 context_md 字段
ALTER TABLE goals DROP COLUMN context_md;
ALTER TABLE projects DROP COLUMN context_md;
ALTER TABLE tasks DROP COLUMN context_md;
