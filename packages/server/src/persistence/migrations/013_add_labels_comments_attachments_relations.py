"""
Migration 013: Add labels, comments, attachments, and task relations tables
Sprint 41-45: Labels + Comments + Sub-issues + Attachments
"""
from sqlalchemy import text

def upgrade(conn):
    # Task labels
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS task_labels (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            name TEXT NOT NULL,
            color TEXT DEFAULT '#64748b',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_labels_task ON task_labels(task_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_labels_name ON task_labels(name)"))

    # Task comments
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS task_comments (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            is_agent_reply INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_comments_task ON task_comments(task_id)"))

    # Task attachments
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS task_attachments (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            mime_type TEXT,
            file_size INTEGER,
            uploaded_by TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_attachments_task ON task_attachments(task_id)"))

    # Task relations (sub-issues + blocking + relates_to)
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS task_relations (
            id TEXT PRIMARY KEY,
            parent_task_id TEXT NOT NULL,
            child_task_id TEXT NOT NULL,
            relation_type TEXT DEFAULT 'subtask',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            FOREIGN KEY (child_task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_relations_parent ON task_relations(parent_task_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_task_relations_child ON task_relations(child_task_id)"))
    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_task_relations_unique ON task_relations(parent_task_id, child_task_id, relation_type)"))

    print("[Migration 013] Labels, comments, attachments, relations tables created")


def downgrade(conn):
    conn.execute(text("DROP TABLE IF EXISTS task_labels"))
    conn.execute(text("DROP TABLE IF EXISTS task_comments"))
    conn.execute(text("DROP TABLE IF EXISTS task_attachments"))
    conn.execute(text("DROP TABLE IF EXISTS task_relations"))
    print("[Migration 013] Tables dropped")
