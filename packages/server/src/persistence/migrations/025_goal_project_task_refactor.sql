-- Sprint 77 P1-1: Goal-Project-Task 1:N 重构
-- Date: 2026-05-13
-- Author: 刚子
-- Status: ✅ goals.project_id 已删除（2026-05-13 执行）
-- Status: ⏳ tasks.goal_id 待删除（风险高，暂缓）

-- 目标：
-- 1. ✅ 删除 goals.project_id（已完成）
-- 2. ⏳ 删除 tasks.goal_id（通过 task.project_id → project.goal_id 推导）

-- ============================================================
-- 步骤 1: 重建 goals 表，删除 project_id
-- ============================================================

-- 检查 goals.project_id 是否有数据
SELECT COUNT(*) as goals_with_project FROM goals WHERE project_id IS NOT NULL;

-- 如果有数据，先备份
-- CREATE TABLE goals_backup AS SELECT * FROM goals;

ALTER TABLE goals RENAME TO goals_old;

CREATE TABLE goals (
    id VARCHAR(32) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description VARCHAR(2000),
    parent_id VARCHAR(32),
    status VARCHAR(20) DEFAULT 'draft',
    progress FLOAT DEFAULT 0.0,
    task_ids JSON,
    created_at DATETIME,
    updated_at DATETIME,
    completed_at DATETIME,
    priority VARCHAR(50),
    due_date DATETIME,
    failed_at DATETIME,
    matched_scenario_id VARCHAR(36),
    workflow_id VARCHAR(36),
    workspace_type VARCHAR(10),
    workspace_path VARCHAR(500),
    workspace_status VARCHAR(20),
    workspace_error TEXT,
    last_clone_at DATETIME,
    last_pull_at DATETIME,
    last_push_at DATETIME,
    verifier_agent_id TEXT,
    mode TEXT,
    optimization_target TEXT,
    convergence_threshold REAL,
    max_rounds INTEGER,
    run_status TEXT
);

INSERT INTO goals (
    id, title, description, parent_id, status, progress, task_ids,
    created_at, updated_at, completed_at, priority, due_date, failed_at,
    matched_scenario_id, workflow_id, workspace_type, workspace_path,
    workspace_status, workspace_error, last_clone_at, last_pull_at,
    last_push_at, verifier_agent_id, mode, optimization_target,
    convergence_threshold, max_rounds, run_status
)
SELECT
    id, title, description, parent_id, status, progress, task_ids,
    created_at, updated_at, completed_at, priority, due_date, failed_at,
    matched_scenario_id, workflow_id, workspace_type, workspace_path,
    workspace_status, workspace_error, last_clone_at, last_pull_at,
    last_push_at, verifier_agent_id, mode, optimization_target,
    convergence_threshold, max_rounds, run_status
FROM goals_old;

DROP TABLE goals_old;

-- ============================================================
-- 步骤 2: 重建 tasks 表，删除 goal_id
-- ============================================================

ALTER TABLE tasks RENAME TO tasks_old;

CREATE TABLE tasks (
    id VARCHAR(32) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description VARCHAR(5000),
    project_id VARCHAR(32),
    assigned_agent VARCHAR(32),
    status VARCHAR(20) DEFAULT 'todo',
    priority INTEGER,
    dependencies JSON,
    depends_on JSON,
    created_at DATETIME,
    updated_at DATETIME,
    started_at DATETIME,
    completed_at DATETIME,
    estimated_hours FLOAT,
    actual_hours FLOAT,
    result VARCHAR(5000),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_type TEXT,
    error_message TEXT,
    blocked_reason TEXT,
    category VARCHAR(50),
    due_date DATETIME,
    parent_id VARCHAR(32),
    workflow_step_id VARCHAR(36),
    result_summary TEXT,
    timeout_reason TEXT,
    recovery_count INTEGER,
    schedule_priority INTEGER,
    assigned_at DATETIME,
    acceptance_criteria TEXT,
    verifier_agent_id TEXT,
    verification_cycle INT,
    ruling_comment_id TEXT,
    instruction_comment_id TEXT,
    ruling_instruction TEXT,
    doc_refs TEXT,
    workspace_path TEXT,
    needs_verification BOOLEAN DEFAULT 1,
    verifier_type TEXT,
    paused_reason VARCHAR(50)
);

INSERT INTO tasks (
    id, title, description, project_id, assigned_agent, status, priority,
    dependencies, depends_on, created_at, updated_at, started_at,
    completed_at, estimated_hours, actual_hours, result, retry_count,
    max_retries, error_type, error_message, blocked_reason, category,
    due_date, parent_id, workflow_step_id, result_summary, timeout_reason,
    recovery_count, schedule_priority, assigned_at, acceptance_criteria,
    verifier_agent_id, verification_cycle, ruling_comment_id,
    instruction_comment_id, ruling_instruction, doc_refs, workspace_path,
    needs_verification, verifier_type, paused_reason
)
SELECT
    id, title, description, project_id, assigned_agent, status, priority,
    dependencies, depends_on, created_at, updated_at, started_at,
    completed_at, estimated_hours, actual_hours, result, retry_count,
    max_retries, error_type, error_message, blocked_reason, category,
    due_date, parent_id, workflow_step_id, result_summary, timeout_reason,
    recovery_count, schedule_priority, assigned_at, acceptance_criteria,
    verifier_agent_id, verification_cycle, ruling_comment_id,
    instruction_comment_id, ruling_instruction, doc_refs, workspace_path,
    needs_verification, verifier_type, paused_reason
FROM tasks_old;

DROP TABLE tasks_old;

-- ============================================================
-- 步骤 3: 添加缺失的索引
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_projects_goal_id ON projects(goal_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);
