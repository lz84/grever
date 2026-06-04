-- Sprint 65 Phase 0.1: heartbeat_logs 增加 raw_payload 列
-- 用于记录心跳响应的原始 JSON 数据
ALTER TABLE heartbeat_logs ADD COLUMN raw_payload TEXT;
