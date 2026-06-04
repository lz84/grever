import sqlite3
conn = sqlite3.connect(r'D:\work\research\agents-nexus\data\reins.db')
c = conn.cursor()

for t in ['goals', 'projects', 'tasks', 'scenarios']:
    try:
        c.execute(f'PRAGMA table_info({t})')
        cols = [r[1] for r in c.fetchall()]
        c.execute(f'SELECT count(*) FROM {t}')
        count = c.fetchone()[0]
        print(f'{t}: {count} rows, cols={cols}')
    except Exception as e:
        print(f'{t}: ERROR - {e}')
conn.close()
