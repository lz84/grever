-- Sprint 65 Phase 0.2: agents 表增加 model_name, health_status, consecutive_offline_count 列
-- model_name: agent 使用的模型名称，心跳时实时更新
-- health_status: 与 status 保持一致的健康状态字段
-- consecutive_offline_count: 连续离线次数，用于判断 offline 状态
ALTER TABLE agents ADD COLUMN model_name VARCHAR(255) DEFAULT '';
ALTER TABLE agents ADD COLUMN health_status VARCHAR(20) DEFAULT 'online';
ALTER TABLE agents ADD COLUMN consecutive_offline_count INTEGER DEFAULT 0;
