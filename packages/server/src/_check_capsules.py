import sqlite3, json
conn = sqlite3.connect(r'D:\work\research\agents-nexus\data\reins.db')
rows = conn.execute("SELECT id, gene_id, summary, confidence, outcome FROM capsules ORDER BY id LIMIT 10").fetchall()
print(f"Total capsules: {conn.execute('SELECT COUNT(*) FROM capsules').fetchone()[0]}")
for r in rows:
    print(f"  {r[0]} | gene={r[1]} | summary={r[2]} | conf={r[3]} | outcome={r[4]}")
conn.close()
