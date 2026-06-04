import sqlite3

db_path = 'data/reins.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if scenarios table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scenarios'")
result = cursor.fetchone()

if result:
    print("Scenarios table exists, adding columns")
    
    # Add columns if they don't exist
    columns = ['level', 'template_dag', 'agent_requirements', 'trust_level', 'source']
    for col in columns:
        try:
            cursor.execute(f"ALTER TABLE scenarios ADD COLUMN {col}")
            print(f"Added column: {col}")
        except Exception as e:
            print(f"Column {col} already exists or error: {e}")
    
    conn.commit()
else:
    print("Creating scenarios table")
    
    # Create scenarios table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scenarios (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(50) NOT NULL,
            status VARCHAR(50) DEFAULT 'draft',
            version VARCHAR(20) DEFAULT 'v1.0',
            description TEXT,
            scenario_desc TEXT,
            triggers TEXT,
            total_executions INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            success_rate FLOAT DEFAULT 0.0,
            avg_duration_ms FLOAT DEFAULT 0.0,
            min_duration_ms FLOAT DEFAULT 0.0,
            max_duration_ms FLOAT DEFAULT 0.0,
            avg_conflicts FLOAT DEFAULT 0.0,
            avg_step_completion FLOAT DEFAULT 0.0,
            usage_count INTEGER DEFAULT 0,
            versions TEXT,
            execution_log TEXT,
            created_at DATETIME DEFAULT (datetime('now')),
            updated_at DATETIME DEFAULT (datetime('now'))
        )
    """)
    
    # Add Sprint 22 columns
    sprint_columns = ['level', 'template_dag', 'agent_requirements', 'trust_level', 'source']
    for col in sprint_columns:
        try:
            cursor.execute(f"ALTER TABLE scenarios ADD COLUMN {col}")
            print(f"Added column: {col}")
        except Exception as e:
            print(f"Column {col} already exists or error: {e}")

conn.commit()

# Verify
cursor.execute("PRAGMA table_info(scenarios)")
print("\nScenarios columns:", [col[1] for col in cursor.fetchall()])

conn.close()
