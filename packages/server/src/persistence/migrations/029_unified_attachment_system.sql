-- 029: Unified Attachment System
-- 将 task_attachments 升级为 attachments + attachment_links

-- 新附件表
CREATE TABLE IF NOT EXISTS attachments (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    mime_type TEXT,
    sha256_hash TEXT NOT NULL UNIQUE,
    file_size INTEGER,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 附件-实体关联表
CREATE TABLE IF NOT EXISTS attachment_links (
    id TEXT PRIMARY KEY,
    attachment_id TEXT NOT NULL REFERENCES attachments(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_attachment_links_entity ON attachment_links(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_attachment_links_attachment ON attachment_links(attachment_id);
CREATE INDEX IF NOT EXISTS idx_attachments_hash ON attachments(sha256_hash);
