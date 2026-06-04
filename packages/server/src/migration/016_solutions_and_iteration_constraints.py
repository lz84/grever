# -*- coding: utf-8 -*-
"""
迁移脚本 016：创建 solutions + iteration_constraints 表

此脚本将：
1. 创建 solutions 表（方案库）
2. 创建 iteration_constraints 表（迭代约束记录）
"""

import sqlite3
import uuid
import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() == 'gbk':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Database path: use the same path as the server
DB_PATH = Path("D:/work/research/agents-nexus/data/reins.db")


def migrate():
    """执行数据库迁移"""
    if not DB_PATH.exists():
        print(f"数据库文件不存在: {DB_PATH}")
        return False

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        # 1. 创建 solutions 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS solutions (
                id TEXT PRIMARY KEY,
                goal_id TEXT REFERENCES goals(id),
                round INTEGER DEFAULT 1,
                name TEXT,
                status TEXT,
                parameters TEXT,
                dimensions TEXT,
                score REAL,
                is_optimal BOOLEAN DEFAULT 0,
                project_ids TEXT,
                task_ids TEXT,
                constraints TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        print("[OK] solutions 表创建成功")

        # 2. 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_solutions_goal ON solutions(goal_id)")
        print("[OK] idx_solutions_goal 索引创建成功")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_solutions_round ON solutions(goal_id, round)")
        print("[OK] idx_solutions_round 索引创建成功")

        # 3. 创建 iteration_constraints 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS iteration_constraints (
                id TEXT PRIMARY KEY,
                goal_id TEXT REFERENCES goals(id),
                round INTEGER,
                constraints TEXT,
                reason TEXT,
                created_by TEXT,
                created_at TIMESTAMP
            )
        """)
        print("[OK] iteration_constraints 表创建成功")

        # 4. 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_constraints_goal ON iteration_constraints(goal_id)")
        print("[OK] idx_constraints_goal 索引创建成功")

        conn.commit()
        print("[OK] 数据库迁移 016 完成")
        return True

    except Exception as e:
        print(f"[ERROR] 迁移过程中出错: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
