-- Migration 040: Remove done_criteria column
-- Sprint 106 followup: done_criteria has no backend usage, remove it.

ALTER TABLE tasks DROP COLUMN done_criteria;
