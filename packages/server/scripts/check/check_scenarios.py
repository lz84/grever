import sqlite3
conn = sqlite3.connect(r'D:\work\research\agents-nexus\data\reins.db')
c = conn.cursor()
c.execute('PRAGMA table_info(scenarios)')
cols = c.fetchall()
print(f'Column count: {len(cols)}')
for col in cols:
    print(f'  {col}')
conn.close()
