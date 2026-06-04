import sqlite3
db = r'D:\work\research\agents-nexus\data\reins.db'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='traces'")
t = c.fetchone()
if t:
    print('traces table exists')
    c.execute('SELECT count(*) FROM traces')
    print('Rows:', c.fetchone()[0])
else:
    print('traces table MISSING - creating it now')
    c.execute('''CREATE TABLE IF NOT EXISTS traces (
        id VARCHAR(36) PRIMARY KEY,
        task_id VARCHAR(36) NOT NULL,
        task_title VARCHAR(255),
        status VARCHAR(20),
        final_state VARCHAR(20),
        started_at DATETIME,
        completed_at DATETIME,
        duration_ms INTEGER,
        created_at DATETIME DEFAULT (datetime('now'))
    )''')
    conn.commit()
    print('Created traces table')
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='traces'")
    print('Verified:', c.fetchone())
conn.close()
