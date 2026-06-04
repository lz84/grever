-- Phase 1: Task 文档引用和工作目录
-- 日期: 2026-05-05
-- 目的: 支持"文档引用"模式，避免 prompt 塞满文字导致 Context overflow
ALTER TABLE tasks ADD COLUMN doc_refs TEXT DEFAULT NULL;
ALTER TABLE tasks ADD COLUMN workspace_path TEXT DEFAULT NULL;
