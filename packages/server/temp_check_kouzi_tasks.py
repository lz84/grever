import sqlite3
db = sqlite3.connect(r'D:\work\research\agents-nexus\packages\server\data\reins.db')
cur = db.cursor()
agent_id = '3745f1f0-b67d-4287-a10b-e71b3ff17e97'

# 1. Check agent info
cur.execute('SELECT id, name, status FROM agents WHERE id=?', (agent_id,))
print('Agent:', cur.fetchone())

# 2. Check pending tasks
statuses = ('todo', 'in_progress', 'review_needed', 'pending')
cur.execute('SELECT id, title, status, assigned_agent FROM tasks WHERE assigned_agent=? AND status IN (?,?,?,?)', (agent_id,) + statuses)
pending = cur.fetchall()
print('Pending tasks for kouzi:', len(pending))
for r in pending:
    print('  ', r)

# 3. All tasks assigned to kouzi
cur.execute('SELECT id, title, status, assigned_agent FROM tasks WHERE assigned_agent=? LIMIT 15', (agent_id,))
all_tasks = cur.fetchall()
print('All tasks for kouzi:')
for r in all_tasks:
    print('  ', r)

# 4. Check what API returns for pending tasks
print()
print('Checking heartbeat pending tasks endpoint...')
cur.execute('SELECT COUNT(*) FROM tasks WHERE assigned_agent=? AND status IN (?,?,?)', (agent_id, 'todo', 'pending', 'review_needed'))
print('Count todo+pending+review_needed:', cur.fetchone()[0])

db.close()
