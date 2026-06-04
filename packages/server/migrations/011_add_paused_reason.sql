-- Sprint 76: 增加 paused_reason 字段
-- 语义：
--   'human'              — 人类主动暂停
--   'orphan_on_restart'  — server 重启时发现 in_progress 孤儿
--   'orphan_on_offline'  — agent 离线时发现孤儿
--   'orphan_on_timeout'  — 任务超时自动暂停
--   NULL                 — 正常任务（不是 paused）
ALTER TABLE tasks ADD COLUMN paused_reason VARCHAR(50) DEFAULT NULL;