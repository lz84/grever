-- Sprint 66: 任务验证强制机制
-- 新增 needs_verification 字段，默认需要验证
-- 与 acceptance_criteria 配合，确保任务必须带验收标准

ALTER TABLE tasks ADD COLUMN needs_verification BOOLEAN DEFAULT 1 NOT NULL;

-- 已有任务保持 needs_verification=1（需要验证），不改变历史行为
-- 新创建的任务默认需要验证，必须设置 acceptance_criteria 才能创建
