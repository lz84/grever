-- Migration 118: Add verification_reports table for Project/Goal level coordination verification
-- Date: 2026-06-24
-- Implements: Sprint 6 task-s6-1

CREATE TABLE verification_reports (
    id TEXT PRIMARY KEY,
    level TEXT NOT NULL CHECK (level IN ('project', 'goal')),
    target_id TEXT NOT NULL,
    verifier_id TEXT NOT NULL,
    round INTEGER NOT NULL DEFAULT 1,
    verdict TEXT NOT NULL CHECK (verdict IN ('passed', 'failed', 'partial')),
    summary TEXT NOT NULL,
    task_results TEXT NOT NULL,
    gaps TEXT NOT NULL,
    recommendations TEXT NOT NULL,
    remedial_tasks TEXT NOT NULL,
    raw_context TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Index for quick lookup by level and target
CREATE INDEX idx_verification_reports_level_target ON verification_reports(level, target_id);

-- Index for quick lookup by target_id
CREATE INDEX idx_verification_reports_target_id ON verification_reports(target_id);
