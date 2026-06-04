"""
迁移脚本：添加 connectivity 字段到 execution_logs

此脚本将：
1. 添加 connectivity_verified 字段
2. 添加 connectivity_check_duration_ms 字段
3. 添加 connectivity_check_error 字段
4. 添加 skipped_reason 字段
"""

import sqlite3
from pathlib import Path


def migrate():
    """执行数据库迁移"""
    db_path = Path("D:/work/research/agents-nexus/data/reins.db")
    
    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        return False
        
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(execution_logs)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'connectivity_verified' not in columns:
            cursor.execute("ALTER TABLE execution_logs ADD COLUMN connectivity_verified INTEGER")
            print("已添加 connectivity_verified 字段")
        else:
            print("connectivity_verified 字段已存在")
        
        if 'connectivity_check_duration_ms' not in columns:
            cursor.execute("ALTER TABLE execution_logs ADD COLUMN connectivity_check_duration_ms INTEGER")
            print("已添加 connectivity_check_duration_ms 字段")
        else:
            print("connectivity_check_duration_ms 字段已存在")
        
        if 'connectivity_check_error' not in columns:
            cursor.execute("ALTER TABLE execution_logs ADD COLUMN connectivity_check_error TEXT")
            print("已添加 connectivity_check_error 字段")
        else:
            print("connectivity_check_error 字段已存在")
        
        if 'skipped_reason' not in columns:
            cursor.execute("ALTER TABLE execution_logs ADD COLUMN skipped_reason TEXT")
            print("已添加 skipped_reason 字段")
        else:
            print("skipped_reason 字段已存在")
        
        conn.commit()
        print("数据库迁移完成")
        return True
        
    except Exception as e:
        print(f"迁移过程中出错: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
