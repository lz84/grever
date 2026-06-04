# -*- coding: utf-8 -*-
"""
迁移脚本 018：goals 新增 run_status 字段（迭代运行状态）

问题：mode 字段被两个逻辑共用——用户设置的模式类型（normal/exploration）
和迭代系统的运行状态（converged/running/paused），导致收敛时覆盖用户设置。

解决方案：
1. 新增 run_status 字段存迭代运行状态
2. convergence_check 等逻辑改写 run_status，保留 mode

运行：python migrations/018_add_run_status.py
"""

import sqlite3
import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() == 'gbk':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_PATH = Path("D:/work/research/agents-nexus/data/reins.db")


def migrate():
    if not DB_PATH.exists():
        print(f"[ERROR] 数据库文件不存在: {DB_PATH}")
        return False

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(goals)")
        goal_columns = [col[1] for col in cursor.fetchall()]

        if 'run_status' not in goal_columns:
            cursor.execute("ALTER TABLE goals ADD COLUMN run_status TEXT DEFAULT 'idle'")
            print("[OK] goals.run_status 字段添加成功")
        else:
            print("[INFO] goals.run_status 字段已存在")

        conn.commit()
        print("[OK] 数据库迁移 018 完成")
        return True

    except Exception as e:
        print(f"[ERROR] 迁移过程中出错: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
