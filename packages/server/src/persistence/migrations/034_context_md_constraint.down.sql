-- Migration 034: context_md 完整性约束（回滚）
-- Sprint 90
-- Date: 2026-05-25

DROP TRIGGER IF EXISTS enforce_context_md_on_complete;
