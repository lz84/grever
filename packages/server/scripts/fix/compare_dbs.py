import sqlite3

for db, label in [
    (r'D:\work\research\agents-nexus\data\reins.db', 'data/reins.db (8MB 原始)'),
    (r'D:\work\research\agents-nexus\data\reins.db', 'data/reins.db (当前用)'),
]:
    conn = sqlite3.connect(db)
    c = conn.cursor()
    rows = []
    for t in ['goals','projects','tasks','scenarios','agents','workflows','artifacts']:
        try: rows.append(f'{t}={c.execute(f"SELECT count(*) FROM {t}").fetchone()[0]}')
        except: rows.append(f'{t}=ERR')
    print(f'{label}')
    print('  ' + ', '.join(rows))
    conn.close()
