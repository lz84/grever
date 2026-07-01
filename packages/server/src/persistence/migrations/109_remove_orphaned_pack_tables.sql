-- Migration 109: Remove orphaned industry pack content tables
-- Remove: sops, checklists, reference_data, prompt_templates
-- These tables had no entity mapping in the system lifecycle (instantiation/execution)
-- Date: 2026-06-10

-- Drop in reverse FK dependency order
DROP TABLE IF EXISTS reference_data;
DROP TABLE IF EXISTS checklists;
DROP TABLE IF EXISTS sops;
DROP TABLE IF EXISTS prompt_templates;
