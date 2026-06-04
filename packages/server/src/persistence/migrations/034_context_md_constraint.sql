-- Migration 034: context_md 完整性约束
-- Sprint 90: 确保需要验证的任务完成时 context_md 不为空
-- Date: 2026-05-25

-- 修复 1：创建 CHECK 约束，阻止 context_md 为空的任务标记为 done
-- SQLite 不支持 ALTER TABLE ADD CONSTRAINT，需要重建表
-- 改为使用 TRIGGER 实现运行时约束

CREATE TRIGGER enforce_context_md_on_complete
BEFORE UPDATE OF status ON tasks
WHEN NEW.status = 'done' 
  AND OLD.needs_verification = 1 
  AND (NEW.context_md IS NULL OR NEW.context_md = '')
BEGIN
    SELECT RAISE(ABORT, 'context_md_required: needs_verification=1 的任务完成时必须填写 context_md');
END;

-- 修复 2：确保 needs_verification 从 NULL 默认改为 1
UPDATE tasks SET needs_verification = 1 
WHERE needs_verification IS NULL 
  AND acceptance_criteria IS NOT NULL 
  AND acceptance_criteria != '';
