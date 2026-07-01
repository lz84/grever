"""Direct SQL migration for goal mode consolidation — run when alembic has multi-head conflict"""
import sqlite3, sys

db_path = r'D:\work\research\agents-nexus\packages\server\data\reins.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check current goals table structure
cur.execute("PRAGMA table_info(goals)")
existing_cols = [row[1] for row in cur.fetchall()]
print("Existing goals columns:", existing_cols)

# Add new columns if not exist
new_cols = ['diversity', 'portfolio_size', 'original_mode']
for col in new_cols:
    if col not in existing_cols:
        if col == 'diversity':
            cur.execute("ALTER TABLE goals ADD COLUMN diversity VARCHAR(20) DEFAULT 'best'")
        elif col == 'portfolio_size':
            cur.execute("ALTER TABLE goals ADD COLUMN portfolio_size INTEGER DEFAULT 3")
        elif col == 'original_mode':
            cur.execute("ALTER TABLE goals ADD COLUMN original_mode VARCHAR(20)")
        print(f"Added column: {col}")
    else:
        print(f"Column already exists: {col}")

# Show mode distribution before migration
cur.execute("SELECT mode, COUNT(*) FROM goals GROUP BY mode")
print("Mode before migration:", cur.fetchall())

# Migrate mode values
cur.execute("UPDATE goals SET original_mode = mode WHERE mode IN ('normal', 'exploration', 'optimization')")
cur.execute("UPDATE goals SET mode = 'engineering' WHERE mode = 'normal'")
cur.execute("UPDATE goals SET mode = 'research' WHERE mode IN ('exploration', 'optimization')")
print(f"Rows updated: {conn.total_changes}")

# Show mode distribution after migration
cur.execute("SELECT mode, COUNT(*) FROM goals GROUP BY mode")
print("Mode after migration:", cur.fetchall())

conn.commit()

# Verify new columns
cur.execute("PRAGMA table_info(goals)")
final_cols = [row[1] for row in cur.fetchall()]
print("Final goals columns:", final_cols)

conn.close()
print("Migration complete.")
