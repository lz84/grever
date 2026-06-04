-- Migration 043: prompt_templates 提示词模板表
-- Sprint 108: 行业包物理化 - 存储可复用的提示词模板

CREATE TABLE IF NOT EXISTS prompt_templates (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    scope           TEXT NOT NULL,  -- task / project / goal
    template        TEXT NOT NULL,
    variables       TEXT,           -- JSON: ["var1", "var2", ...]
    tags            TEXT,           -- JSON array of tags
    pack_id         TEXT,
    created_at      INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at      INTEGER,
    FOREIGN KEY (pack_id) REFERENCES industry_packs(id)
);

CREATE INDEX IF NOT EXISTS idx_pt_scope ON prompt_templates(scope);
CREATE INDEX IF NOT EXISTS idx_pt_pack ON prompt_templates(pack_id);
