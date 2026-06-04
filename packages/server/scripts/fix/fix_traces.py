import sqlite3
conn = sqlite3.connect(r'D:\work\research\agents-nexus\data\reins.db')
c = conn.cursor()

# Update success based on status
c.execute("UPDATE traces SET success = 1 WHERE status = 'completed'")
c.execute("UPDATE traces SET success = 0 WHERE status IN ('failed', 'blocked')")
conn.commit()

# Verify
c.execute('SELECT status, success, count(*) FROM traces GROUP BY status')
for r in c.fetchall():
    print(r)

# Also update task_trace table if it exists
try:
    c.execute("UPDATE traces SET result_summary = '任务已完成' WHERE status = 'completed'")
    c.execute("UPDATE traces SET result_summary = '任务执行中' WHERE status = 'running'")
    c.execute("UPDATE traces SET result_summary = '任务待处理' WHERE status = 'pending'")
    conn.commit()
    print('Updated result_summary')
except Exception as e:
    print(f'result_summary update skipped: {e}')

conn.close()
print('Done!')
