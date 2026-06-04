import sys
sys.path.insert(0, 'src')
from database.config import DB_CONFIG
print('DB path:', DB_CONFIG.sqlite_path)

import sqlite3, json
conn = sqlite3.connect(DB_CONFIG.sqlite_path)
c = conn.cursor()
c.execute('SELECT id, name FROM workflows LIMIT 1')
row = c.fetchone()
if row:
    print('Found workflow:', row[1])
    c.execute('SELECT dag FROM workflows WHERE id=?', (row[0],))
    r = c.fetchone()
    if r and r[0]:
        dag = json.loads(r[0])
        print(f'  Nodes: {len(dag.get("nodes", []))}')
        print(f'  Edges: {len(dag.get("edges", []))}')
    else:
        print('  NO DAG DATA')
else:
    print('No workflows found')
conn.close()
