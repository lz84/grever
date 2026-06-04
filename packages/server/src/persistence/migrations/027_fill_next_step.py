"""
Fill next_step from depends_on (one-time migration script).

Reads depends_on from projects and tasks, derives next_step (forward links),
and writes them back. Does NOT delete depends_on.
"""
import json
import sqlite3

DB_PATH = "D:/work/research/agents-nexus/data/reins.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# ── Projects ──
print("=== Projects ===")
projects = conn.execute(
    "SELECT id, depends_on FROM projects"
).fetchall()
print(f"  Total projects: {len(projects)}")

next_steps: dict[str, list] = {}
dep_count = 0
for row in projects:
    pid = row["id"]
    deps_raw = row["depends_on"]
    deps = json.loads(deps_raw) if deps_raw and deps_raw != "[]" else []
    for dep_id in deps:
        next_steps.setdefault(dep_id, []).append(pid)
        dep_count += 1

print(f"  Projects with depends_on: {dep_count}")

for pid, nxt in next_steps.items():
    conn.execute(
        "UPDATE projects SET next_step = ? WHERE id = ?",
        (json.dumps(nxt), pid),
    )

proj_updated = conn.execute(
    "SELECT COUNT(*) FROM projects WHERE next_step != '[]'"
).fetchone()[0]
print(f"  Projects with non-empty next_step: {proj_updated}")

# ── Tasks ──
print("\n=== Tasks ===")
tasks = conn.execute(
    "SELECT id, depends_on FROM tasks"
).fetchall()
print(f"  Total tasks: {len(tasks)}")

next_steps = {}
dep_count = 0
for row in tasks:
    tid = row["id"]
    deps_raw = row["depends_on"]
    deps = json.loads(deps_raw) if deps_raw and deps_raw != "[]" else []
    for dep_id in deps:
        next_steps.setdefault(dep_id, []).append(tid)
        dep_count += 1

print(f"  Tasks with depends_on: {dep_count}")

for tid, nxt in next_steps.items():
    conn.execute(
        "UPDATE tasks SET next_step = ? WHERE id = ?",
        (json.dumps(nxt), tid),
    )

task_updated = conn.execute(
    "SELECT COUNT(*) FROM tasks WHERE next_step != '[]'"
).fetchone()[0]
print(f"  Tasks with non-empty next_step: {task_updated}")

conn.commit()

# ── Verification ──
print("\n=== Verification ===")
# Check a few examples
sample_projects = conn.execute(
    "SELECT id, depends_on, next_step FROM projects WHERE depends_on IS NOT NULL AND depends_on != '[]' LIMIT 3"
).fetchall()
for row in sample_projects:
    print(f"  Project {row['id']}: depends_on={row['depends_on']}, next_step={row['next_step']}")

sample_tasks = conn.execute(
    "SELECT id, depends_on, next_step FROM tasks WHERE depends_on IS NOT NULL AND depends_on != '[]' LIMIT 3"
).fetchall()
for row in sample_tasks:
    print(f"  Task {row['id']}: depends_on={row['depends_on']}, next_step={row['next_step']}")

conn.close()
print("\nData fill completed successfully!")
