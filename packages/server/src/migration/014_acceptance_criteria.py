"""
迁移脚本：为 tasks 表添加 acceptance_criteria 字段

此脚本将：
1. 为 tasks 表添加 acceptance_criteria 列
"""

import sqlite3
from pathlib import Path


def migrate():
    """执行数据库迁移"""
    # 获取数据库路径 - 从配置中获取正确的路径
    db_path = Path("D:/work/research/agents-nexus/data/reins.db")
    
    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        return False
        
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # 检查 tasks 表是否存在 acceptance_criteria 列
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'acceptance_criteria' not in columns:
            # 添加 acceptance_criteria 列
            cursor.execute("ALTER TABLE tasks ADD COLUMN acceptance_criteria TEXT")
            print("已为 tasks 表添加 acceptance_criteria 列")
        else:
            print("acceptance_criteria 列已存在")
        
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