"""
迁移脚本：添加 review_needed 状态和 result_summary 字段

此脚本将：
1. 添加 result_summary 字段到 tasks 表
2. 确保 status 字段可以存储 'review_needed' 状态
"""

import sqlite3
from pathlib import Path


def migrate():
    """执行数据库迁移"""
    # 获取数据库路径
    db_path = Path("D:/work/research/agents-nexus/data/reins.db")
    
    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        return False
        
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # 检查是否已存在 result_summary 字段
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'result_summary' not in columns:
            # 添加 result_summary 字段
            cursor.execute("ALTER TABLE tasks ADD COLUMN result_summary TEXT DEFAULT NULL")
            print("已添加 result_summary 字段")
        else:
            print("result_summary 字段已存在")
        
        # 提交更改
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