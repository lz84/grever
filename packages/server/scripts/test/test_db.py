import sqlite3

conn = sqlite3.connect('data/reins.db')
cursor = conn.cursor()

# Check if agent_assignments table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_assignments'")
exists = cursor.fetchone()
print(f"agent_assignments table exists: {exists is not None}")

if exists:
    # Check columns
    cursor.execute("PRAGMA table_info(agent_assignments)")
    columns = cursor.fetchall()
    print("Columns:", [col[1] for col in columns])
    
    # Try inserting a record
    cursor.execute("""
        INSERT INTO agent_assignments (id, agent_id, status)
        VALUES ('test-001', 'agent-001', 'pending')
    """)
    conn.commit()
    print("Insert successful")
    
    # Query it back
    cursor.execute("SELECT * FROM agent_assignments")
    print("Records:", cursor.fetchall())

conn.close()
