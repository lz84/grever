"""
迁移脚本：创建 scenario_cognitions 关联表

此脚本将：
1. 创建 scenario_cognitions 表用于关联场景和认知
"""

import sqlite3
from pathlib import Path
import uuid


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
        # 创建 scenario_cognitions 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scenario_cognitions (
                id TEXT PRIMARY KEY,
                scenario_id TEXT REFERENCES scenarios(id) ON DELETE CASCADE,
                cognition_id INTEGER NOT NULL,
                relevance_score REAL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        print("已创建 scenario_cognitions 表")
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scenario_cognitions_scenario 
            ON scenario_cognitions(scenario_id)
        """)
        print("已创建 scenario_cognitions_scenario 索引")
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scenario_cognitions_cognition 
            ON scenario_cognitions(cognition_id)
        """)
        print("已创建 scenario_cognitions_cognition 索引")
        
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