import sqlite3
db = sqlite3.connect('data/reins.db')
cur = db.cursor()
# Check agents table
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%agent%'")
tables = cur.fetchall()
print('Agent-related tables:', tables)
cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
print('Total tables:', cur.fetchone()[0])
# Check all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
all_tables = cur.fetchall()
for t in all_tables:
    cur2 = db.cursor()
    cur2.execute('SELECT COUNT(*) FROM ' + t[0])
    print('  ', t[0], ':', cur2.fetchone()[0], 'rows')
db.close()
