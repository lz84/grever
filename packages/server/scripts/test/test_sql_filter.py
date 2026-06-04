import sqlite3

db_path = r'D:\work\research\agents-nexus\data\reins.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check all projects
cursor.execute("SELECT id, name, goal_id FROM projects")
rows = cursor.fetchall()
print(f"All projects ({len(rows)}):")
for r in rows:
    print(f'  {r[0]:20s} {r[1]:20s} goal_id={r[2]!r}')

# Test filtering
for test_gid in ['goal-ddfef4fb53dd', 'goal-001', 'nonexistent']:
    cursor.execute("SELECT COUNT(*) FROM projects WHERE goal_id = ?", (test_gid,))
    count = cursor.fetchone()[0]
    print(f'\nSQL filter goal_id={test_gid!r}: {count} projects')

conn.close()
