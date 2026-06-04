import sqlite3, json

conn = sqlite3.connect(r'D:\work\research\agents-nexus\data\reins.db')
c = conn.cursor()

c.execute('SELECT id, name, status FROM workflows')
for wf_id, wname, wst in c.fetchall():
    c.execute('SELECT dag FROM workflows WHERE id=?', (wf_id,))
    row = c.fetchone()
    if row and row[0]:
        dag = json.loads(row[0])
        nodes = dag.get('nodes', [])
        edges = dag.get('edges', [])
        print(f'Workflow: {wname} ({len(nodes)} nodes, {len(edges)} edges)')
        if nodes:
            print(f'  First node: {nodes[0]}')
    else:
        print(f'Workflow: {wname} - NO DAG DATA')

conn.close()
