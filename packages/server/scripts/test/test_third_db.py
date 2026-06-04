import sqlite3

db_path = r'D:\work\research\agents-nexus\packages\server\src\data\reins.db'
print(f'Checking: {db_path}')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check schema
cursor.execute("PRAGMA table_info(projects)")
columns = cursor.fetchall()
print(f'Columns ({len(columns)}):')
for col in columns:
    print(f'  {col}')

# Count projects
cursor.execute("SELECT COUNT(*) FROM projects")
total = cursor.fetchone()[0]
print(f'\nTotal projects: {total}')

# Test goal_id filtering
cursor.execute("SELECT id, name, goal_id FROM projects LIMIT 5")
rows = cursor.fetchall()
print('\nSample projects:')
for row in rows:
    print(f'  {row[0]:20s} {row[1]:30s} goal_id={row[2]}')

# Test filtering
for test_gid in ['goal-ddfef4fb53dd', 'e1092ac865ce49e8a04c5bb672ac276b']:
    cursor.execute("SELECT COUNT(*) FROM projects WHERE goal_id = ?", (test_gid,))
    count = cursor.fetchone()[0]
    print(f'\nFilter goal_id={test_gid[:20]}... -> {count} projects')

conn.close()
