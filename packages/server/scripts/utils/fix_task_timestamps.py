"""
Fix tasks table: convert string timestamps (ISO datetime) to integer (Unix timestamp).
"""
import sqlite3
from datetime import datetime

db = 'D:/work/research/agents-nexus/data/reins.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# Find rows with string timestamps
cur.execute("SELECT id, updated_at, started_at FROM tasks WHERE typeof(updated_at) = 'text' OR typeof(started_at) = 'text'")
rows = cur.fetchall()

print(f"Found {len(rows)} rows with string timestamps")

fixed_updated = 0
fixed_started = 0

for task_id, updated_at, started_at in rows:
    # Fix updated_at
    if updated_at and isinstance(updated_at, str):
        try:
            dt = datetime.strptime(updated_at, '%Y-%m-%d %H:%M:%S.%f')
            unix_ts = int(dt.timestamp())
            cur.execute("UPDATE tasks SET updated_at = ? WHERE id = ?", (unix_ts, task_id))
            fixed_updated += 1
        except Exception as e:
            print(f"  ERROR converting updated_at for {task_id}: {updated_at} - {e}")

    # Fix started_at
    if started_at and isinstance(started_at, str):
        try:
            dt = datetime.strptime(started_at, '%Y-%m-%d %H:%M:%S.%f')
            unix_ts = int(dt.timestamp())
            cur.execute("UPDATE tasks SET started_at = ? WHERE id = ?", (unix_ts, task_id))
            fixed_started += 1
        except Exception as e:
            print(f"  ERROR converting started_at for {task_id}: {started_at} - {e}")

conn.commit()
print(f"\nFixed: {fixed_updated} updated_at, {fixed_started} started_at")

# Verify
cur.execute("SELECT COUNT(*) FROM tasks WHERE typeof(updated_at) = 'text'")
remaining_updated = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM tasks WHERE typeof(started_at) = 'text'")
remaining_started = cur.fetchone()[0]
print(f"Remaining string updated_at: {remaining_updated}")
print(f"Remaining string started_at: {remaining_started}")

# Verify the specific task
cur.execute("SELECT id, updated_at, started_at FROM tasks WHERE id = 'task-b0bafdca10e1'")
row = cur.fetchone()
print(f"\nVerify task-b0bafdca10e1: updated_at={row[1]} ({type(row[1]).__name__}), started_at={row[2]} ({type(row[2]).__name__})")

conn.close()
print("\nDone!")
