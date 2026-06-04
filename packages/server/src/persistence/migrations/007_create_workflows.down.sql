-- Migration: 007_create_workflows (DOWN)
-- Description: 回滚 Workflow 和 WorkflowStep 表

DROP TABLE IF EXISTS workflow_steps;
DROP TABLE IF EXISTS workflows;
