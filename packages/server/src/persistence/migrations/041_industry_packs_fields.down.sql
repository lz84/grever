-- Migration 041 Down: 移除 industry_packs 扩展字段
-- SQLite 不支持 DROP COLUMN 所有类型，需重建表

-- 注意：SQLite 3.35.0+ 支持 DROP COLUMN，以下语法需要 SQLite >= 3.35.0
ALTER TABLE industry_packs DROP COLUMN format_version;
ALTER TABLE industry_packs DROP COLUMN author;
ALTER TABLE industry_packs DROP COLUMN license;
ALTER TABLE industry_packs DROP COLUMN compatibility_min_version;
ALTER TABLE industry_packs DROP COLUMN compatibility_max_version;
ALTER TABLE industry_packs DROP COLUMN source_checksum;
ALTER TABLE industry_packs DROP COLUMN source_signature;
ALTER TABLE industry_packs DROP COLUMN import_source;
ALTER TABLE industry_packs DROP COLUMN import_source_file;
ALTER TABLE industry_packs DROP COLUMN dependencies;
