"""
Migration 020: 创建 verification_task_log 表 + tasks.verifier_type 字段

步骤：
1. 创建 verification_task_log 表
2. 创建索引 idx_vlog_agent(agent_id) 和 idx_vlog_task(task_id)
3. tasks 表新增 verifier_type 列（TEXT DEFAULT 'default'）
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(r"D:\work\research\agents-nexus\data\reins.db")


def migrate():
    if not DB_PATH.exists():
        print(f"ERROR: DB not found: {DB_PATH}")
        return False

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        # Step 1: 创建 verification_task_log 表
        print("Step 1: Creating verification_task_log table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verification_task_log (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                agent_id TEXT,
                verifier_type TEXT,
                input_summary TEXT,
                output_raw TEXT,
                passed BOOLEAN,
                message TEXT,
                duration_seconds REAL,
                created_at TIMESTAMP DEFAULT (datetime('now'))
            )
        """)
        print("  Created verification_task_log table")

        # Step 2: 创建索引
        print("Step 2: Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vlog_agent
            ON verification_task_log(agent_id)
        """)
        print("  Created idx_vlog_agent(agent_id)")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vlog_task
            ON verification_task_log(task_id)
        """)
        print("  Created idx_vlog_task(task_id)")

        # Step 3: tasks 表新增 verifier_type 列
        print("Step 3: Adding verifier_type column to tasks...")

        # 检查列是否已存在
        cursor.execute("PRAGMA table_info(tasks)")
        existing_columns = [row[1] for row in cursor.fetchall()]

        if "verifier_type" in existing_columns:
            print("  Column verifier_type already exists, skipping")
        else:
            cursor.execute("""
                ALTER TABLE tasks ADD COLUMN verifier_type TEXT DEFAULT 'default'
            """)
            print("  Added verifier_type TEXT DEFAULT 'default' to tasks")

        conn.commit()

        # Step 4: 验证
        print("Step 4: Verifying...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='verification_task_log'")
        table_exists = cursor.fetchone()
        print(f"  verification_task_log table exists: {'YES' if table_exists else 'NO'}")

        cursor.execute("PRAGMA table_info(tasks)")
        for col in cursor.fetchall():
            if col[1] == "verifier_type":
                print(f"  tasks.verifier_type: type={col[2]}, default={col[4]}")
                break
        else:
            print("  WARNING: verifier_type column not found in tasks!")

        cursor.execute("PRAGMA index_list(verification_task_log)")
        indexes = cursor.fetchall()
        idx_names = [idx[1] for idx in indexes]
        print(f"  Indexes on verification_task_log: {idx_names}")

        print("DONE: Migration 020 complete")
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
