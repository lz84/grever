-- Down: 回滚 035_tag_lifecycle 迁移
-- 注意：SQLite 不支持 DROP COLUMN（< 3.35.0），使用重建表方案

-- 1. 删除触发器
DROP TRIGGER IF EXISTS validate_custom_pack_insert;
DROP TRIGGER IF EXISTS validate_custom_pack_update;

-- 2. 删除索引
DROP INDEX IF EXISTS idx_ict_replaced_by;
DROP INDEX IF EXISTS idx_ip_pack_type;
DROP INDEX IF EXISTS idx_ip_base_pack;

-- 3. 重建 industry_packs（移除 pack_type, base_pack_id）
CREATE TABLE industry_packs_backup (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0.0',
    description TEXT,
    tags_count INTEGER DEFAULT 0,
    scenarios_count INTEGER DEFAULT 0,
    skills_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'draft',
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER
);

INSERT INTO industry_packs_backup (id, name, industry, version, description, tags_count, scenarios_count, skills_count, status, created_at, updated_at)
SELECT id, name, industry, version, description, tags_count, scenarios_count, skills_count, status, created_at, updated_at
FROM industry_packs;

DROP TABLE industry_packs;
ALTER TABLE industry_packs_backup RENAME TO industry_packs;

-- 4. 重建 industry_capability_tags（移除 replaced_by, version_major, version_minor, version_patch）
CREATE TABLE industry_capability_tags_backup (
    id TEXT PRIMARY KEY,
    industry TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    tag_name_en TEXT,
    description TEXT NOT NULL,
    dimension TEXT NOT NULL,
    level TEXT DEFAULT 'basic',
    prerequisites TEXT DEFAULT '[]',
    tools TEXT DEFAULT '[]',
    examples TEXT DEFAULT '[]',
    status TEXT DEFAULT 'active',
    created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER
);

INSERT INTO industry_capability_tags_backup (id, industry, tag_name, tag_name_en, description, dimension, level, prerequisites, tools, examples, status, created_at, updated_at)
SELECT id, industry, tag_name, tag_name_en, description, dimension, level, prerequisites, tools, examples, status, created_at, updated_at
FROM industry_capability_tags;

DROP TABLE industry_capability_tags;
ALTER TABLE industry_capability_tags_backup RENAME TO industry_capability_tags;
