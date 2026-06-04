-- Migration 044: sops 标准操作程序表
-- Sprint 108: 行业包物理化 - 存储行业标准化操作流程

CREATE TABLE IF NOT EXISTS sops (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    industry        TEXT,
    content         TEXT NOT NULL,
    version         TEXT,
    tags            TEXT,           -- JSON array of tags
    related_tasks   TEXT,           -- JSON array of task IDs
    pack_id         TEXT,
    created_at      INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at      INTEGER,
    FOREIGN KEY (pack_id) REFERENCES industry_packs(id)
);

CREATE INDEX IF NOT EXISTS idx_sop_industry ON sops(industry);
CREATE INDEX IF NOT EXISTS idx_sop_pack ON sops(pack_id);
