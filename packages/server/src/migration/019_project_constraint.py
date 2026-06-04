"""
Migration 019: 添加 project_id NOT NULL 约束

SQLite 不支持直接 ALTER TABLE ... ADD CONSTRAINT，
需要重建表。

步骤：
1. 创建 "Nexus 内部" 项目（如果不存在）
2. 将 project_id IS NULL 的任务挂到该项目
3. 重建 tasks 表，添加 NOT NULL 约束
4. 验证约束生效
"""
import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(r"D:\work\research\agents-nexus\data\reins.db")
INTERNAL_PROJECT_ID = "proj-nexus-internal"


def migrate():
    if not DB_PATH.exists():
        print(f"ERROR: DB not found: {DB_PATH}")
        return False

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys=OFF")
    cursor = conn.cursor()

    try:
        now = datetime.now().isoformat()

        # Step 1: 创建 "Nexus 内部" 项目
        print("Step 1: Creating internal project...")
        cursor.execute("SELECT id FROM projects WHERE id = ?", (INTERNAL_PROJECT_ID,))
        existing = cursor.fetchone()
        
        if not existing:
            goal_id = "goal-nexus-internal"
            cursor.execute("SELECT id FROM goals WHERE id = ?", (goal_id,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT OR IGNORE INTO goals (id, title, description, status, mode, progress, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (goal_id, "Nexus 内部任务", "系统内部任务（无关联项目的任务）", "active", "normal", 0.0, now, now)
                )
            
            cursor.execute(
                """INSERT INTO projects (id, name, description, goal_id, status, members, created_at, updated_at, priority, mode)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (INTERNAL_PROJECT_ID, "Nexus 内部", "系统内部项目，承载无关联项目的任务",
                 goal_id, "active", json.dumps([], ensure_ascii=False), now, now, "P2", "normal")
            )
            print(f"  Created project 'Nexus 内部' ({INTERNAL_PROJECT_ID})")
        else:
            print(f"  Project already exists")

        # Step 2: 迁移无 project_id 的任务
        print("Step 2: Migrating NULL project_id tasks...")
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE project_id IS NULL")
        null_count = cursor.fetchone()[0]
        print(f"  Found {null_count} tasks with NULL project_id")
        
        if null_count > 0:
            cursor.execute("UPDATE tasks SET project_id = ? WHERE project_id IS NULL", (INTERNAL_PROJECT_ID,))
            print(f"  Migrated {null_count} tasks to internal project")
        conn.commit()

        # Step 3: 重建 tasks 表添加 NOT NULL 约束
        print("Step 3: Rebuilding tasks table with NOT NULL constraint...")
        
        # 获取原表结构
        cursor.execute("PRAGMA table_info(tasks)")
        columns = cursor.fetchall()
        col_defs = []
        col_names = []
        for col in columns:
            cid, name, col_type, notnull, dflt_value, pk = col
            col_names.append(name)
            if name == "project_id":
                col_defs.append(f"    {name} {col_type} NOT NULL DEFAULT '{INTERNAL_PROJECT_ID}'")
            elif pk:
                col_defs.append(f"    {name} {col_type} PRIMARY KEY")
            else:
                col_defs.append(f"    {name} {col_type}")
        
        create_sql = f"CREATE TABLE tasks_new (\n" + ",\n".join(col_defs) + "\n)"
        
        # 创建新表
        cursor.execute(create_sql)
        
        # 复制数据
        cols_str = ", ".join(col_names)
        cursor.execute(f"INSERT INTO tasks_new ({cols_str}) SELECT {cols_str} FROM tasks")
        print(f"  Copied {cursor.rowcount} rows")
        
        # 删除旧表，重命名新表
        cursor.execute("DROP TABLE tasks")
        cursor.execute("ALTER TABLE tasks_new RENAME TO tasks")
        conn.commit()
        print("  Table rebuilt with NOT NULL constraint")

        # Step 4: 验证
        print("Step 4: Verifying...")
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE project_id IS NULL")
        remaining = cursor.fetchone()[0]
        if remaining > 0:
            print(f"  WARNING: {remaining} tasks still have NULL project_id!")
        else:
            print(f"  OK: 0 tasks with NULL project_id")
        
        # 验证 NOT NULL 约束
        cursor.execute("PRAGMA table_info(tasks)")
        for col in cursor.fetchall():
            if col[1] == "project_id":
                print(f"  project_id notnull={col[3]} (should be 1)")
                break
        
        conn.commit()
        print("DONE: Migration 019 complete")
        return True

    except Exception as e:
        print(f"ERROR: {e}")
        conn.rollback()
        return False
    finally:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.close()


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
