-- Migration 086: Industry Capability Tags
-- Sprint 93: 行业能力标签库基础设施
-- Date: 2026-05-25

-- 行业能力标签库
CREATE TABLE IF NOT EXISTS industry_capability_tags (
    id              TEXT PRIMARY KEY,
    industry        TEXT NOT NULL,
    tag_name        TEXT NOT NULL,
    tag_name_en     TEXT,
    description     TEXT NOT NULL,
    dimension       TEXT NOT NULL,
    level           TEXT DEFAULT 'basic',
    prerequisites   TEXT DEFAULT '[]',
    tools           TEXT DEFAULT '[]',
    examples        TEXT DEFAULT '[]',
    status          TEXT DEFAULT 'active',
    created_at      INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_ict_industry ON industry_capability_tags(industry);
CREATE INDEX IF NOT EXISTS idx_ict_dimension ON industry_capability_tags(dimension);
CREATE INDEX IF NOT EXISTS idx_ict_status ON industry_capability_tags(status);

-- 行业包元数据
CREATE TABLE IF NOT EXISTS industry_packs (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    industry        TEXT NOT NULL,
    version         TEXT NOT NULL DEFAULT '1.0.0',
    description     TEXT,
    tags_count      INTEGER DEFAULT 0,
    scenarios_count INTEGER DEFAULT 0,
    skills_count    INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'draft',
    created_at      INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_ip_industry ON industry_packs(industry);
CREATE INDEX IF NOT EXISTS idx_ip_status ON industry_packs(status);

-- 行业包内容关联
CREATE TABLE IF NOT EXISTS industry_pack_contents (
    pack_id         TEXT NOT NULL,
    content_type    TEXT NOT NULL,
    content_id      TEXT NOT NULL,
    PRIMARY KEY (pack_id, content_type, content_id),
    FOREIGN KEY (pack_id) REFERENCES industry_packs(id)
);
