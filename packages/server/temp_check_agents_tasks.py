import sqlite3
db = sqlite3.connect('data/reins.db')
cur = db.cursor()
cur.execute('SELECT id, name, status FROM agents')
agents = cur.fetchall()
print('All agents:')
for a in agents:
    print('  ', a)
    agent_id = a[0]
    agent_name = a[1]
    cur2 = db.cursor()
    cur2.execute('SELECT COUNT(*) FROM tasks WHERE assigned_agent=?', (agent_id,))
    total = cur2.fetchone()[0]
    statuses = ('todo', 'pending', 'review_needed', 'in_progress')
    cur2.execute('SELECT COUNT(*) FROM tasks WHERE assigned_agent=? AND status IN (?,?,?,?)', (agent_id,) + statuses)
    pending = cur2.fetchone()[0]
    print('    total:', total, ' pending:', pending)
    if pending > 0:
        cur2.execute('SELECT id, title, status FROM tasks WHERE assigned_agent=? AND status IN (?,?,?,?) LIMIT 5', (agent_id,) + statuses)
        for t in cur2.fetchall():
            print('      ', t)
db.close()
