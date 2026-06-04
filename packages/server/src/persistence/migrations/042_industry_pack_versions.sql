-- Migration 042: industry_pack_versions 版本历史表
-- Sprint 108: 行业包物理化 - 记录行业包的每次版本变更

CREATE TABLE IF NOT EXISTS industry_pack_versions (
    id              TEXT PRIMARY KEY,
    pack_id         TEXT NOT NULL,
    version         TEXT NOT NULL,
    action          TEXT NOT NULL,  -- created / imported / upgraded
    source_file     TEXT,
    source_checksum TEXT,
    stats           TEXT,           -- JSON: {tags_count, scenarios_count, skills_count}
    imported_at     INTEGER,
    notes           TEXT,
    created_at      INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (pack_id) REFERENCES industry_packs(id)
);

CREATE INDEX IF NOT EXISTS idx_ipv_pack ON industry_pack_versions(pack_id);
CREATE INDEX IF NOT EXISTS idx_ipv_version ON industry_pack_versions(version);
