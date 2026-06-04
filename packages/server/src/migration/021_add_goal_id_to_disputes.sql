-- Sprint 74: disputes 表新增 goal_id 字段
-- 让 dispute 直接关联 goal，不只能通过 task 间接关联
-- 2026-05-11

ALTER TABLE disputes ADD COLUMN goal_id VARCHAR(32) DEFAULT NULL;

-- 已有数据：通过 related_task_id 反推 goal_id
UPDATE disputes SET goal_id = (
    SELECT t.goal_id FROM tasks t WHERE t.id = disputes.related_task_id
)
WHERE goal_id IS NULL AND related_task_id IS NOT NULL;

-- 索引：加速按 goal_id 查询
CREATE INDEX IF NOT EXISTS idx_disputes_goal_id ON disputes(goal_id);
