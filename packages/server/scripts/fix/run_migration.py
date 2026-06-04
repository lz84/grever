import sqlite3

db_path = 'data/reins.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== Sprint 22 Migration ===\n")

# 1. Goals: add matched_scenario_id, workflow_id
print("1. Updating goals table...")
try:
    cursor.execute("ALTER TABLE goals ADD COLUMN matched_scenario_id VARCHAR(36)")
    print("  - Added matched_scenario_id")
except Exception as e:
    print(f"  - matched_scenario_id: {e}")

try:
    cursor.execute("ALTER TABLE goals ADD COLUMN workflow_id VARCHAR(36)")
    print("  - Added workflow_id")
except Exception as e:
    print(f"  - workflow_id: {e}")

# Verify goals
cursor.execute("PRAGMA table_info(goals)")
print("  Goals columns:", [col[1] for col in cursor.fetchall()])

# 2. Projects: add workflow_id, phase_order, matched_scenario_id
print("\n2. Updating projects table...")
try:
    cursor.execute("ALTER TABLE projects ADD COLUMN workflow_id VARCHAR(36)")
    print("  - Added workflow_id")
except Exception as e:
    print(f"  - workflow_id: {e}")

try:
    cursor.execute("ALTER TABLE projects ADD COLUMN phase_order INTEGER")
    print("  - Added phase_order")
except Exception as e:
    print(f"  - phase_order: {e}")

try:
    cursor.execute("ALTER TABLE projects ADD COLUMN matched_scenario_id VARCHAR(36)")
    print("  - Added matched_scenario_id")
except Exception as e:
    print(f"  - matched_scenario_id: {e}")

# Verify projects
cursor.execute("PRAGMA table_info(projects)")
print("  Projects columns:", [col[1] for col in cursor.fetchall()])

# 3. Workflows: add project_id, parent_scenario_id, level
print("\n3. Updating workflows table...")
try:
    cursor.execute("ALTER TABLE workflows ADD COLUMN project_id VARCHAR(36)")
    print("  - Added project_id")
except Exception as e:
    print(f"  - project_id: {e}")

try:
    cursor.execute("ALTER TABLE workflows ADD COLUMN parent_scenario_id VARCHAR(36)")
    print("  - Added parent_scenario_id")
except Exception as e:
    print(f"  - parent_scenario_id: {e}")

try:
    cursor.execute("ALTER TABLE workflows ADD COLUMN level VARCHAR(20)")
    print("  - Added level")
except Exception as e:
    print(f"  - level: {e}")

# Create indexes
try:
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_project_id ON workflows(project_id)")
    print("  - Created index idx_workflows_project_id")
except Exception as e:
    print(f"  - idx_workflows_project_id: {e}")

try:
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_parent_scenario_id ON workflows(parent_scenario_id)")
    print("  - Created index idx_workflows_parent_scenario_id")
except Exception as e:
    print(f"  - idx_workflows_parent_scenario_id: {e}")

# Verify workflows
cursor.execute("PRAGMA table_info(workflows)")
print("  Workflows columns:", [col[1] for col in cursor.fetchall()])

# 4. Tasks: add workflow_step_id
print("\n4. Updating tasks table...")
try:
    cursor.execute("ALTER TABLE tasks ADD COLUMN workflow_step_id VARCHAR(36)")
    print("  - Added workflow_step_id")
except Exception as e:
    print(f"  - workflow_step_id: {e}")

# Verify tasks
cursor.execute("PRAGMA table_info(tasks)")
print("  Tasks columns:", [col[1] for col in cursor.fetchall()])

# 5. Create agent_assignments table
print("\n5. Creating agent_assignments table...")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_assignments (
        id VARCHAR(36) PRIMARY KEY,
        goal_id VARCHAR(36),
        project_id VARCHAR(36),
        task_id VARCHAR(36),
        agent_id VARCHAR(36) NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        priority VARCHAR(20),
        assigned_at DATETIME,
        completed_at DATETIME,
        feedback TEXT,
        created_at DATETIME DEFAULT (datetime('now')),
        updated_at DATETIME DEFAULT (datetime('now'))
    )
""")
print("  - Created agent_assignments table")

# Create indexes
try:
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_assignments_goal_id ON agent_assignments(goal_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_assignments_project_id ON agent_assignments(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_assignments_task_id ON agent_assignments(task_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_assignments_agent_id ON agent_assignments(agent_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_assignments_status ON agent_assignments(status)")
    print("  - Created indexes")
except Exception as e:
    print(f"  - Indexes: {e}")

conn.commit()
conn.close()

print("\n=== Migration Complete ===")
