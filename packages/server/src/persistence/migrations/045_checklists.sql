-- Migration 045: checklists 检查清单表
-- Sprint 108: 行业包物理化 - 存储任务/项目的预检和事后检查清单

CREATE TABLE IF NOT EXISTS checklists (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    scope           TEXT NOT NULL,  -- pre_task / post_task / pre_project
    items           TEXT NOT NULL,  -- JSON: [{text, required, checked}, ...]
    tags            TEXT,           -- JSON array of tags
    related_tasks   TEXT,           -- JSON array of task IDs
    pack_id         TEXT,
    created_at      INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    updated_at      INTEGER,
    FOREIGN KEY (pack_id) REFERENCES industry_packs(id)
);

CREATE INDEX IF NOT EXISTS idx_cl_scope ON checklists(scope);
CREATE INDEX IF NOT EXISTS idx_cl_pack ON checklists(pack_id);
