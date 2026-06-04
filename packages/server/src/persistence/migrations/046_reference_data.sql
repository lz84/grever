-- Migration 046: reference_data 参考数据表
-- Sprint 108: 行业包物理化 - 存储行业参考数据（查找表、常量、数据表）

CREATE TABLE IF NOT EXISTS reference_data (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL,  -- table / lookup / constants
    data            TEXT NOT NULL,  -- JSON: structured data
    tags            TEXT,           -- JSON array of tags
    pack_id         TEXT,
    created_at      INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at      INTEGER,
    FOREIGN KEY (pack_id) REFERENCES industry_packs(id)
);

CREATE INDEX IF NOT EXISTS idx_rd_type ON reference_data(type);
CREATE INDEX IF NOT EXISTS idx_rd_pack ON reference_data(pack_id);
