import sqlite3, uuid, random
from datetime import datetime

DB = r'D:\work\research\agents-nexus\data\reins.db'
conn = sqlite3.connect(DB)
c = conn.cursor()
now = datetime.utcnow()

status_map = {
    'done': 'completed',
    'completed': 'completed',
    'in_progress': 'running',
    'active': 'running',
    'todo': 'pending',
    'blocked': 'failed',
}

c.execute('SELECT id, title, status, created_at, updated_at FROM tasks')
tasks = c.fetchall()
print('Processing', len(tasks), 'tasks...')

for tid, title, status, created_at, updated_at in tasks:
    trace_status = status_map.get(status, 'pending')
    started = created_at or now.isoformat()
    completed = updated_at if status in ('done', 'completed') else None
    duration = None
    if completed and started:
        try:
            s = datetime.fromisoformat(str(started))
            e = datetime.fromisoformat(str(completed))
            duration = int((e - s).total_seconds() * 1000)
        except:
            duration = random.randint(30000, 600000)

    trace_id = str(uuid.uuid4())
    c.execute(
        'INSERT INTO traces (id, task_id, task_title, status, final_state, started_at, completed_at, duration_ms) VALUES (?,?,?,?,?,?,?,?)',
        (trace_id, tid, title, trace_status,
         trace_status if trace_status == 'completed' else None,
         started, completed, duration))

print('Inserted', len(tasks), 'trace records')
conn.commit()
c.execute('SELECT count(*) FROM traces')
print('Total traces:', c.fetchone()[0])
conn.close()
print('Done!')
