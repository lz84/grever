"""
Migration 018: 统一 Nexus agent ID 为 OpenClaw UUID

旧 ID → 新 ID (OpenClaw UUID)
  gangzi → fefd19b0-7c1a-4927-b294-c795c76afb9f (刚子)
  guzi   → 876b9322-0fbe-4cd0-97c2-9244a4e3b905 (谷子)
  mazi   → 9d899c03-4ada-45a7-805a-b2f0fb4ebb24 (麻子)
  wenzi  → 8817e140-2c46-40d8-9444-a6bca8a8e8fb (蚊子)
  kouzi  → 3745f1f0-b67d-4287-a10b-e71b3ff17e97 (扣子)
"""
import sqlite3
import sys
from pathlib import Path

AGENT_MAP = {
    'gangzi': 'fefd19b0-7c1a-4927-b294-c795c76afb9f',
    'guzi': '876b9322-0fbe-4cd0-97c2-9244a4e3b905',
    'mazi': '9d899c03-4ada-45a7-805a-b2f0fb4ebb24',
    'wenzi': '8817e140-2c46-40d8-9444-a6bca8a8e8fb',
    'kouzi': '3745f1f0-b67d-4287-a10b-e71b3ff17e97',
}

DB_PATH = Path(r"D:\work\research\agents-nexus\data\reins.db")


def migrate():
    """统一 agent ID 为 UUID"""
    if not DB_PATH.exists():
        print(f"数据库文件不存在: {DB_PATH}")
        return False

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        # 1. agents 表
        print("更新 agents 表...")
        for old_id, new_id in AGENT_MAP.items():
            cursor.execute("UPDATE agents SET id = ? WHERE id = ?", (new_id, old_id))
            if cursor.rowcount > 0:
                print(f"  {old_id} → {new_id} ({cursor.rowcount} 行)")
        conn.commit()

        # 2. tasks 表
        print("更新 tasks 表...")
        for old_id, new_id in AGENT_MAP.items():
            cursor.execute("UPDATE tasks SET assigned_agent = ? WHERE assigned_agent = ?", (new_id, old_id))
            if cursor.rowcount > 0:
                print(f"  {old_id} → {new_id} ({cursor.rowcount} 行)")
        conn.commit()

        # 3. workflows 表
        print("更新 workflows 表...")
        for old_id, new_id in AGENT_MAP.items():
            cursor.execute("UPDATE workflows SET created_by = ? WHERE created_by = ?", (new_id, old_id))
            if cursor.rowcount > 0:
                print(f"  {old_id} → {new_id} ({cursor.rowcount} 行)")
        conn.commit()

        # 4. workflow_steps 表
        print("更新 workflow_steps 表...")
        for old_id, new_id in AGENT_MAP.items():
            cursor.execute("UPDATE workflow_steps SET agent_id = ? WHERE agent_id = ?", (new_id, old_id))
            if cursor.rowcount > 0:
                print(f"  {old_id} → {new_id} ({cursor.rowcount} 行)")
        conn.commit()

        # 5. disputes 表
        print("更新 disputes 表...")
        for old_id, new_id in AGENT_MAP.items():
            cursor.execute("UPDATE disputes SET resolved_by = ? WHERE resolved_by = ?", (new_id, old_id))
            if cursor.rowcount > 0:
                print(f"  {old_id} → {new_id} ({cursor.rowcount} 行)")
        conn.commit()

        # 6. system_config 表
        print("更新 system_config 表...")
        cursor.execute(
            "UPDATE system_config SET value = ? WHERE category = 'root_agent' AND key = 'agent_id'",
            ('"fefd19b0-7c1a-4927-b294-c795c76afb9f"',)
        )
        if cursor.rowcount > 0:
            print(f"  root_agent ID 更新 ({cursor.rowcount} 行)")
        conn.commit()

        # 7. projects 表 members JSON (需要 JSON 替换)
        print("更新 projects 表 members JSON...")
        cursor.execute("SELECT id, members FROM projects WHERE members IS NOT NULL")
        rows = cursor.fetchall()
        for proj_id, members_json in rows:
            import json
            try:
                members = json.loads(members_json)
                updated = False
                for old_id, new_id in AGENT_MAP.items():
                    if old_id in members:
                        members = [new_id if m == old_id else m for m in members]
                        updated = True
                if updated:
                    cursor.execute(
                        "UPDATE projects SET members = ? WHERE id = ?",
                        (json.dumps(members, ensure_ascii=False), proj_id)
                    )
                    print(f"  project {proj_id} members 更新")
            except (json.JSONDecodeError, TypeError):
                pass
        conn.commit()

        print("DONE: Agent ID 统一完成")
        return True

    except Exception as e:
        print(f"ERROR: migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
