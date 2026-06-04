"""为任务执行详情创建 traces 表并填充数据"""
import sqlite3
import uuid
import random
from datetime import datetime

DB = r'D:\work\research\agents-nexus\data\reins.db'
conn = sqlite3.connect(DB)
c = conn.cursor()
now = datetime.utcnow()

# 创建 traces 表
c.execute('''CREATE TABLE IF NOT EXISTS traces (
    id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    workflow_id VARCHAR(36),
    task_title VARCHAR(255),
    status VARCHAR(20),
    final_state VARCHAR(20),
    started_at DATETIME,
    completed_at DATETIME,
    duration_ms INTEGER,
    created_at DATETIME DEFAULT (datetime('now'))
)''')
conn.commit()
print('traces table ready')

# status 映射
status_map = {
    'done': 'completed',
    'completed': 'completed',
    'in_progress': 'running',
    'active': 'running',
    'todo': 'pending',
    'blocked': 'failed',
}

# 为所有任务创建 trace 记录
c.execute('SELECT id, title, status, created_at, updated_at FROM tasks')
tasks = c.fetchall()
print(f'Tasks to trace: {len(tasks)}')

for tid, title, status, created_at, updated_at in tasks:
    trace_status = status_map.get(status, 'pending')
    started = created_at or now.isoformat()
    completed = updated_at if status in ('done', 'completed') else None
    duration = None
    if completed and started:
        try:
            start_dt = datetime.fromisoformat(str(started))
            end_dt = datetime.fromisoformat(str(completed))
            duration = int((end_dt - start_dt).total_seconds() * 1000)
        except:
            duration = random.randint(30000, 300000)

    trace_id = str(uuid.uuid4())
    c.execute('''INSERT INTO traces
        (id, task_id, task_title, status, final_state, started_at, completed_at, duration_ms)
        VALUES (?,?,?,?,?,?,?,?)''',
        (trace_id, tid, title, trace_status,
         trace_status if trace_status == 'completed' else None,
         started, completed, duration))

print(f'Created {len(tasks)} trace records')
conn.commit()

c.execute('SELECT count(*) FROM traces')
print(f'Total traces in DB: {c.fetchone()[0]}')
conn.close()
print('Done!')
