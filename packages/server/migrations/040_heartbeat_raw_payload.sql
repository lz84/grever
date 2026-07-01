-- Phase 0.1: heartbeat_logs 增加 raw_payload 列
-- 添加 raw_payload TEXT 列到 heartbeat_logs 表，用于记录心跳完整原始响应

ALTER TABLE heartbeat_logs
ADD COLUMN raw_payload TEXT;
