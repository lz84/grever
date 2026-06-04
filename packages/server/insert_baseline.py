import sqlite3
conn = sqlite3.connect('D:/work/research/agents-nexus/data/reins.db')
cur = conn.cursor()
cur.execute(
    "INSERT OR IGNORE INTO schema_migrations (version, name, checksum, version_num) VALUES (?, ?, ?, ?)",
    ('000_alembic_init', 'alembic_baseline', 'd41d8cd98f00b204e9800998ecf8427e', '000_alembic_init')
)
conn.commit()
print('Rows inserted:', cur.rowcount)
conn.close()