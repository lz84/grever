-- Migration: 117_remove_pack_contents_table
-- Desc: Remove redundant industry_pack_contents table. Each content type (skills, knowledge, agent_schemes) now has its own pack_id FK.

DROP TABLE IF EXISTS industry_pack_contents;
