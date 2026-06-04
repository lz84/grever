# -*- coding: utf-8 -*-
"""
迁移脚本 017：goals/projects 新增模式与优化字段

此脚本将：
1. goals 表新增 mode, optimization_target, convergence_threshold, max_rounds 字段
2. projects 表新增 mode 字段
"""

import sqlite3
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
        # 检查 goals 表现有列
        cursor.execute("PRAGMA table_info(goals)")
        goal_columns = [col[1] for col in cursor.fetchall()]

        # 1. goals.mode
        if 'mode' not in goal_columns:
            cursor.execute("ALTER TABLE goals ADD COLUMN mode TEXT DEFAULT 'normal'")
            print("[OK] goals.mode 字段添加成功")
        else:
            print("[INFO] goals.mode 字段已存在")

        # 2. goals.optimization_target
        if 'optimization_target' not in goal_columns:
            cursor.execute("ALTER TABLE goals ADD COLUMN optimization_target TEXT")
            print("[OK] goals.optimization_target 字段添加成功")
        else:
            print("[INFO] goals.optimization_target 字段已存在")

        # 3. goals.convergence_threshold
        if 'convergence_threshold' not in goal_columns:
            cursor.execute("ALTER TABLE goals ADD COLUMN convergence_threshold REAL DEFAULT 0.05")
            print("[OK] goals.convergence_threshold 字段添加成功")
        else:
            print("[INFO] goals.convergence_threshold 字段已存在")

        # 4. goals.max_rounds
        if 'max_rounds' not in goal_columns:
            cursor.execute("ALTER TABLE goals ADD COLUMN max_rounds INTEGER DEFAULT 10")
            print("[OK] goals.max_rounds 字段添加成功")
        else:
            print("[INFO] goals.max_rounds 字段已存在")

        # 检查 projects 表现有列
        cursor.execute("PRAGMA table_info(projects)")
        project_columns = [col[1] for col in cursor.fetchall()]

        # 5. projects.mode
        if 'mode' not in project_columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN mode TEXT DEFAULT 'normal'")
            print("[OK] projects.mode 字段添加成功")
        else:
            print("[INFO] projects.mode 字段已存在")

        conn.commit()
        print("[OK] 数据库迁移 017 完成")
        return True

    except Exception as e:
        print(f"[ERROR] 迁移过程中出错: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
