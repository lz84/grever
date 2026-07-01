"""
Migration 119: Sprint 5 s5-1 调度循环配置

在 system_config 表新增以下配置项：
- dispatch.max_attempts: 最大重派次数（默认 2）
- task.timeout_minutes: 任务超时时间（分钟，默认 30）
- agent.heartbeat_timeout_minutes: Agent 心跳超时时间（分钟，默认 10）

使用 INSERT OR IGNORE 保证幂等性。
"""
import os
import sqlite3
import uuid
import sys

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.environ.get("SQLITE_PATH", r"D:\work\research\agents-nexus\data\reins.db")

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL")

seed_data = [
    (
        f"cfg-dispatch-{uuid.uuid4().hex[:8]}",
        "dispatch",
        "dispatch.max_attempts",
        "2",
        "最大重派次数（超时后换 Agent 重派上限）",
    ),
    (
        f"cfg-task-{uuid.uuid4().hex[:8]}",
        "task",
        "task.timeout_minutes",
        "30",
        "任务超时时间（分钟），超过该时间无更新视为超时",
    ),
    (
        f"cfg-agent-{uuid.uuid4().hex[:8]}",
        "agent",
        "agent.heartbeat_timeout_minutes",
        "10",
        "Agent 心跳超时时间（分钟），超过该时间无心跳视为离线",
    ),
]

inserted = 0
skipped = 0
for item_id, category, key, value, desc in seed_data:
    try:
        conn.execute(
            """INSERT OR IGNORE INTO system_config
               (id, category, key, value, description, updated_at, updated_by)
               VALUES (?, ?, ?, ?, ?, datetime('now'), 'migration_119')""",
            (item_id, category, key, value, desc),
        )
        if conn.total_changes > 0:
            inserted += 1
        else:
            skipped += 1
    except Exception as e:
        print(f"  WARNING {key}: {e}")
        skipped += 1

conn.commit()

# 验证
cur = conn.cursor()
for _, category, key, value, _ in seed_data:
    cur.execute(
        "SELECT key, value FROM system_config WHERE key = ?",
        (key,),
    )
    row = cur.fetchone()
    if row:
        print(f"OK system_config: {row[0]} = {row[1]}")
    else:
        print(f"MISSING system_config: {key}")

conn.close()
print(f"\nMigration 119 applied: inserted={inserted}, skipped={skipped}")
