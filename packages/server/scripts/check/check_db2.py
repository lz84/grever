import sqlite3

conn = sqlite3.connect(r'D:\work\research\agents-nexus\data\reins.db')
cursor = conn.cursor()

cursor.execute('SELECT id, name, status FROM projects WHERE id IN ("proj-2882a8ff", "proj-3ce3c6d4", "proj-16b87293", "proj-2f5833d6")')
print('Projects:', cursor.fetchall())

cursor.execute('SELECT id, title, project_id, status FROM tasks WHERE project_id IN ("proj-2882a8ff", "proj-3ce3c6d4", "proj-16b87293", "proj-2f5833d6")')
print('Tasks:', cursor.fetchall())

conn.close()
