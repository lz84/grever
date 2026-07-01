-- Migration 117 down: Restore industry_pack_contents table
-- This migration reverses the removal of the pack contents association table.

CREATE TABLE IF NOT EXISTS industry_pack_contents (
    pack_id    TEXT NOT NULL REFERENCES industry_packs(id) ON DELETE CASCADE,
    content_type TEXT NOT NULL,
    content_id TEXT NOT NULL,
    PRIMARY KEY (pack_id, content_type, content_id)
);
