-- Migration 117: Remove industry_pack_contents table (2026-06-16)
-- Reason: Redundant. All content types (skills, knowledge, agent_schemes)
-- already have pack_id FK on their own tables. Tags and scenarios are
-- global references, not pack-owned data.

DROP TABLE IF EXISTS industry_pack_contents;
