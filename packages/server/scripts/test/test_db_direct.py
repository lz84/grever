import sqlite3
import os

# Find the database
db_path = r'D:\work\research\agents-nexus\data\reins.db'
print(f'DB path: {db_path}')
print(f'Exists: {os.path.exists(db_path)}')

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check projects table schema
    cursor.execute("PRAGMA table_info(projects)")
    columns = cursor.fetchall()
    print('\nProjects table columns:')
    for col in columns:
        print(f'  {col}')
    
    # Check all projects
    cursor.execute("SELECT id, name, goal_id FROM projects")
    rows = cursor.fetchall()
    print(f'\nProjects ({len(rows)} total):')
    for row in rows:
        print(f'  ID: {row[0][:20]}...  Name: {row[1][:25]:25s}  goal_id: {row[2]}')
    
    # Test filtering
    test_gid = 'goal-ddfef4fb53dd'
    cursor.execute("SELECT COUNT(*) FROM projects WHERE goal_id = ?", (test_gid,))
    count = cursor.fetchone()[0]
    print(f'\nDirect SQL filter by goal_id={test_gid}: {count} projects')
    
    test_gid2 = 'e1092ac865ce49e8a04c5bb672ac276b'
    cursor.execute("SELECT COUNT(*) FROM projects WHERE goal_id = ?", (test_gid2,))
    count2 = cursor.fetchone()[0]
    print(f'Direct SQL filter by goal_id={test_gid2[:20]}...: {count2} projects')
    
    conn.close()
