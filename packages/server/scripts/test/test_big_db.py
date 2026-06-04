import sqlite3

# Check the large database
db_path = r'D:\work\research\data\reins.db'
print(f'Checking: {db_path}')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check schema
cursor.execute("PRAGMA table_info(projects)")
columns = [col[1] for col in cursor.fetchall()]
print(f'Columns: {columns}')

# Count projects
cursor.execute("SELECT COUNT(*) FROM projects")
total = cursor.fetchone()[0]
print(f'Total projects: {total}')

# Test goal_id filtering
for test_gid in ['goal-ddfef4fb53dd', 'e1092ac865ce49e8a04c5bb672ac276b', '07479f1714fe4e5a8acc66c17eabcf69']:
    cursor.execute("SELECT COUNT(*) FROM projects WHERE goal_id = ?", (test_gid,))
    count = cursor.fetchone()[0]
    print(f'  goal_id={test_gid[:20]}... -> {count} projects')

conn.close()
