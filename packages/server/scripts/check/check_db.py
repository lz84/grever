import sqlite3

conn = sqlite3.connect(r'D:\work\research\agents-nexus\data\reins.db')
cursor = conn.cursor()

cursor.execute('SELECT id, name, status FROM projects WHERE status IN ("active", "in_progress") LIMIT 5')
print('Projects:', cursor.fetchall())

cursor.execute('SELECT id, title, project_id, status FROM tasks WHERE status = "in_progress" LIMIT 10')
print('In-progress Tasks:', cursor.fetchall())

conn.close()
