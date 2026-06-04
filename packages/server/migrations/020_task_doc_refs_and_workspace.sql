-- 任务文档引用和工作目录 (Doc Refs Mode)
-- 解决 Worker prompt Context overflow 问题
-- Agent 通过 read 工具按需读取设计文档，而非塞满整个 prompt

ALTER TABLE tasks ADD COLUMN doc_refs TEXT DEFAULT NULL;  -- JSON array of doc paths: ["docs/plan.md#section1"]
ALTER TABLE tasks ADD COLUMN workspace_path TEXT DEFAULT NULL;  -- 工作目录，继承自 Project/Goal
