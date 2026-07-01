-- Migration: 015_create_execution_logs
-- Full-chain execution logging for Grever
-- Records: heartbeat, task_start, task_progress, task_complete

CREATE TABLE IF NOT EXISTS execution_logs (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) COMMENT '关联任务ID（heartbeat时可为NULL）',
    agent_id VARCHAR(36) NOT NULL COMMENT 'Agent ID',
    action VARCHAR(50) NOT NULL COMMENT '动作类型: heartbeat, task_start, task_progress, task_complete',
    input JSON COMMENT '输入数据',
    output JSON COMMENT '输出数据',
    status VARCHAR(20) NOT NULL DEFAULT 'success' COMMENT '状态: success, failure',
    duration_ms INTEGER DEFAULT 0 COMMENT '耗时（毫秒）',
    created_at DATETIME NOT NULL DEFAULT (datetime('now')) COMMENT '创建时间',
    error_message TEXT COMMENT '错误信息',
    result_summary TEXT COMMENT '结果摘要',
    metadata JSON COMMENT '额外元数据（如connectivity_verified, assigned_task_ids等）',
    connectivity_verified BOOLEAN DEFAULT 0 COMMENT 'P1-01: 连接是否验证',
    INDEX idx_execution_logs_agent_created (agent_id, created_at),
    INDEX idx_execution_logs_task_action (task_id, action),
    INDEX idx_execution_logs_action (action)
);

-- Rollback
-- DROP TABLE IF EXISTS execution_logs;
