import sqlite3

conn = sqlite3.connect(r'D:\work\research\agents-nexus\packages\server\data\reins.db')

# List all tables
cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)

# Get goals columns
if 'goals' in tables:
    cur = conn.execute("PRAGMA table_info(goals)")
    cols = [r[1] for r in cur.fetchall()]
    print("goals columns:", cols)

    # Check existing mode values
    cur = conn.execute("SELECT mode, COUNT(*) FROM goals GROUP BY mode")
    print("mode distribution:", cur.fetchall())

conn.close()
print("Done")
