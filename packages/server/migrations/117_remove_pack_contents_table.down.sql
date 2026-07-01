-- Down Migration: 117_remove_pack_contents_table
-- Desc: Re-create industry_pack_contents table (restoring to pre-117 state).

CREATE TABLE IF NOT EXISTS industry_pack_contents (
    pack_id TEXT NOT NULL REFERENCES industry_packs(id),
    content_type TEXT NOT NULL CHECK(content_type IN ('tag', 'scenario', 'knowledge', 'agent_scheme', 'skill')),
    content_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pack_id, content_type, content_id)
);
