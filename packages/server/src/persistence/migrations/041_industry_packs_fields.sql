-- Migration 041: industry_packs 扩展字段
-- Sprint 108: 行业包物理化 - 给 industry_packs 新增 10 个元数据字段

ALTER TABLE industry_packs ADD COLUMN format_version TEXT DEFAULT '1.0';
ALTER TABLE industry_packs ADD COLUMN author TEXT;
ALTER TABLE industry_packs ADD COLUMN license TEXT DEFAULT 'proprietary';
ALTER TABLE industry_packs ADD COLUMN compatibility_min_version TEXT;
ALTER TABLE industry_packs ADD COLUMN compatibility_max_version TEXT;
ALTER TABLE industry_packs ADD COLUMN source_checksum TEXT;
ALTER TABLE industry_packs ADD COLUMN source_signature TEXT;
ALTER TABLE industry_packs ADD COLUMN import_source TEXT DEFAULT 'created';
ALTER TABLE industry_packs ADD COLUMN import_source_file TEXT;
ALTER TABLE industry_packs ADD COLUMN dependencies TEXT DEFAULT '[]';
