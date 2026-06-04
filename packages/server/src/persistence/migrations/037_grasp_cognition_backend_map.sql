-- Sprint 102-1: GrASP Phase 2 路由切换 - cognitions_backend_map 表
-- 记录 cognition_id 到 backend_name 的映射

CREATE TABLE IF NOT EXISTS cognition_backend_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cognition_id TEXT NOT NULL UNIQUE,
    backend_name TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_cognition_backend_map_cognition_id ON cognition_backend_map(cognition_id);
CREATE INDEX IF NOT EXISTS idx_cognition_backend_map_backend_name ON cognition_backend_map(backend_name);

-- 触发器：自动更新 updated_at
CREATE TRIGGER IF NOT EXISTS tr_cognition_backend_map_updated_at
AFTER UPDATE ON cognition_backend_map
BEGIN
    UPDATE cognition_backend_map SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
