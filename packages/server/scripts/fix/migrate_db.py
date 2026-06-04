import sqlite3

db_path = r'D:\work\research\agents-nexus\data\reins.db'
print(f'Migrating: {db_path}')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check existing columns
cursor.execute("PRAGMA table_info(projects)")
existing = {col[1] for col in cursor.fetchall()}
print(f'Existing columns: {existing}')

# Add missing columns
missing_cols = [
    ('priority', "VARCHAR(20) DEFAULT 'medium'"),
    ('assignee', "VARCHAR(255)"),
    ('due_date', "VARCHAR(50)"),
    ('workflow_id', "VARCHAR(36)"),
    ('phase_order', "INTEGER"),
    ('matched_scenario_id', "VARCHAR(36)"),
]

for col_name, col_type in missing_cols:
    if col_name not in existing:
        try:
            cursor.execute(f"ALTER TABLE projects ADD COLUMN {col_name} {col_type}")
            print(f'Added column: {col_name}')
        except Exception as e:
            print(f'Error adding {col_name}: {e}')
    else:
        print(f'Column exists: {col_name}')

conn.commit()

# Verify
cursor.execute("PRAGMA table_info(projects)")
columns = [col[1] for col in cursor.fetchall()]
print(f'\nFinal columns: {columns}')

# Check projects
cursor.execute("SELECT COUNT(*) FROM projects")
count = cursor.fetchone()[0]
print(f'Total projects: {count}')

cursor.execute("SELECT id, name, goal_id FROM projects")
rows = cursor.fetchall()
for r in rows:
    print(f'  {r[0]:20s} {r[1]:20s} goal_id={r[2]}')

conn.close()
print('\nMigration complete!')
