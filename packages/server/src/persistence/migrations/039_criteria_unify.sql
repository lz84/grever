-- Migration 039: Criteria 字段统一
-- Sprint 106: 统一任务 criteria 字段
-- 1. 新增 done_criteria TEXT 列（存 JSON）
-- 2. 数据迁移：从 description 解析 ## Done Criteria checkbox 块 → done_criteria JSON
-- 3. 数据迁移：从 description 解析 ## Acceptance Criteria JSON 块 → acceptance_criteria

-- Step 1: 新增 done_criteria 列
ALTER TABLE tasks ADD COLUMN done_criteria TEXT DEFAULT NULL;

-- Step 2: 数据迁移
-- 从 description 的 ## Done Criteria 块解析 checkbox，生成 JSON 写入 done_criteria
-- 从 description 的 ## Acceptance Criteria 块提取 JSON，写入 acceptance_criteria（如果 DB 列为空）

-- 使用 Python 脚本执行数据迁移，因为 SQLite 不支持正则解析
-- 此迁移的 SQL 部分仅负责 schema 变更
-- 数据迁移由 migration runner 的 Python hook 执行

-- 注意：SQLite 不支持 ALTER TABLE 的复杂逻辑，数据迁移需通过 Python 完成
-- 迁移脚本启动时会自动调用 persistence/migrations/_039_data_migration.py
