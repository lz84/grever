-- Migration 087: Fix human_input_requests schema mismatch
-- Add missing rejected_reason column
-- Date: 2026-06-08

ALTER TABLE human_input_requests ADD COLUMN rejected_reason TEXT;
