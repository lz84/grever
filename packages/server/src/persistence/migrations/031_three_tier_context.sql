-- Migration 031: 三级上下文文档
-- 为 tasks / projects / goals 增加 context_md 字段，
-- 用于存储结构化上下文（URL、端点、验证步骤、成果物等）。

ALTER TABLE tasks ADD COLUMN context_md TEXT;
ALTER TABLE projects ADD COLUMN context_md TEXT;
ALTER TABLE goals ADD COLUMN context_md TEXT;
