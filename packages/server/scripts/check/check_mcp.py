import sqlite3
conn = sqlite3.connect(r'D:\work\research\agents-nexus\data\reins.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'mcp%'")
tables = c.fetchall()
print('MCP tables:', tables)
conn.close()
