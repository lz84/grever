import sqlite3
conn = sqlite3.connect('/home/user/tianshu/data/reins.db')
cur = conn.cursor()
# Check mcp tables
for t in ['mcp_servers', 'mcp_tools']:
    cur.execute(f"PRAGMA table_info({t})")
    cols = cur.fetchall()
    print(f'{t}: {len(cols)} columns')
    if not cols:
        # Table doesn't exist
        cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{t}'")
        exists = cur.fetchone()
        print(f'  Table exists: {exists}')
    for col in cols:
        print(f'    {col}')
conn.close()