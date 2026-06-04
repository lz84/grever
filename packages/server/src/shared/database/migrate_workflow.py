"""
Workflow 数据模型迁移脚本

用法:
    python -m database.migrate_workflow
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# 默认数据库路径
DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "nexus.db"
)


def get_db_path() -> str:
    """获取数据库路径"""
    # 从环境变量或默认路径
    return os.environ.get("NEXUS_DB_PATH", DEFAULT_DB_PATH)


def migrate(db_path: str = None) -> None:
    """
    执行 Workflow 表迁移

    创建表:
        - workflows
        - workflow_steps
    """
    db_path = db_path or get_db_path()

    # 确保 data 目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        logger.info(f"Running Workflow migration on: {db_path}")

        # 创建 workflows 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id              TEXT PRIMARY KEY,
                goal_id         TEXT,
                status          TEXT NOT NULL DEFAULT 'draft',
                name            TEXT NOT NULL,
                description     TEXT,
                dag             TEXT,
                metadata        TEXT,
                created_by      TEXT,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                started_at      TEXT,
                completed_at    TEXT
            )
        """)
        logger.info("Table 'workflows' created or already exists")

        # 创建 workflow_steps 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_steps (
                id              TEXT PRIMARY KEY,
                workflow_id     TEXT NOT NULL,
                name            TEXT NOT NULL,
                description     TEXT,
                status          TEXT NOT NULL DEFAULT 'pending',
                dependencies    TEXT,
                "order"         INTEGER,
                agent_id        TEXT,
                input_data      TEXT,
                output_data     TEXT,
                error           TEXT,
                retry_count     INTEGER NOT NULL DEFAULT 0,
                max_retries     INTEGER NOT NULL DEFAULT 3,
                timeout_seconds INTEGER,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                started_at      TEXT,
                completed_at    TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
            )
        """)
        logger.info("Table 'workflow_steps' created or already exists")

        # 创建索引
        indexes = [
            ("idx_workflows_goal_id", "workflows", "goal_id"),
            ("idx_workflows_status_created", "workflows", "status, created_at"),
            ("idx_workflow_steps_workflow_id", "workflow_steps", "workflow_id"),
            ("idx_workflow_steps_status", "workflow_steps", "status"),
            ("idx_workflow_steps_workflow_order", "workflow_steps", "workflow_id, \"order\""),
        ]

        for idx_name, table, cols in indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({cols})")
                logger.info(f"Index '{idx_name}' created or already exists")
            except sqlite3.OperationalError as e:
                logger.warning(f"Index '{idx_name}' skipped: {e}")

        conn.commit()
        logger.info("Workflow migration completed successfully")

    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


def verify(db_path: str = None) -> bool:
    """验证表是否存在"""
    db_path = db_path or get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = ["workflows", "workflow_steps"]
    all_ok = True

    for table in tables:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        if cursor.fetchone():
            logger.info(f"✓ Table '{table}' exists")
        else:
            logger.error(f"✗ Table '{table}' missing")
            all_ok = False

    conn.close()
    return all_ok


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Workflow 数据模型迁移")
    parser.add_argument("--db-path", help="数据库路径")
    parser.add_argument("--verify", action="store_true", help="仅验证表是否存在")
    args = parser.parse_args()

    if args.verify:
        ok = verify(args.db_path)
        sys.exit(0 if ok else 1)
    else:
        migrate(args.db_path)
