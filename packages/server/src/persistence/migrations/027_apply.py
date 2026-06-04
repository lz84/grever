"""
Apply migration 027: Add next_step column to projects and tasks
"""
import sqlite3

DB_PATH = "D:/work/research/agents-nexus/data/reins.db"

conn = sqlite3.connect(DB_PATH)

# Add next_step to projects
try:
    conn.execute("ALTER TABLE projects ADD COLUMN next_step TEXT DEFAULT '[]'")
    conn.commit()
    print("✓ projects.next_step added")
except Exception as e:
    print(f"  projects.next_step: {e}")

# Add next_step to tasks
try:
    conn.execute("ALTER TABLE tasks ADD COLUMN next_step TEXT DEFAULT '[]'")
    conn.commit()
    print("✓ tasks.next_step added")
except Exception as e:
    print(f"  tasks.next_step: {e}")

# Verify
cur = conn.cursor()
cur.execute("PRAGMA table_info(projects)")
proj_cols = [r[1] for r in cur.fetchall()]
print(f"projects columns: {proj_cols}")
assert 'next_step' in proj_cols, "next_step not in projects!"

cur.execute("PRAGMA table_info(tasks)")
task_cols = [r[1] for r in cur.fetchall()]
print(f"tasks columns: {task_cols}")
assert 'next_step' in task_cols, "next_step not in tasks!"

conn.close()
print("Migration 027 applied successfully!")
