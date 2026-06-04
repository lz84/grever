import sqlite3, os

agent_id = '3745f1f0-b67d-4287-a10b-e71b3ff17e97'

paths = [
    (r'D:\work\research\agents-nexus\packages\server\data\reins.db', 'packages/server'),
    (r'D:\work\research\agents-nexus\data\reins.db', 'data/'),
]

for p, name in paths:
    if not os.path.exists(p):
        continue
    db = sqlite3.connect(p)
    cur = db.cursor()
    cur.execute('SELECT COUNT(*) FROM agents')
    agents_count = cur.fetchone()[0]
    cur.execute('SELECT id, name FROM agents')
    agents = cur.fetchall()
    cur.execute('SELECT COUNT(*) FROM tasks WHERE assigned_agent=?', (agent_id,))
    kouzi_tasks = cur.fetchone()[0]
    cur.execute('SELECT id, title, status, assigned_agent FROM tasks WHERE assigned_agent=? LIMIT 5', (agent_id,))
    tasks = cur.fetchall()
    print('=== ' + name + ' ===')
    print('  Agents:', agents_count)
    print('  Tasks for kouzi:', kouzi_tasks)
    for t in tasks:
        print('    ', t)
    # Check pending tasks
    cur.execute('SELECT id, title, status FROM tasks WHERE assigned_agent=? AND status IN (\'todo\',\'pending\',\'review_needed\',\'in_progress\')', (agent_id,))
    pending = cur.fetchall()
    print('  Pending:', len(pending))
    for t in pending:
        print('    ', t)
    db.close()
    print()
