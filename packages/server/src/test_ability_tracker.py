"""
Test script for AbilityTracker — Sprint 75 Task 4
"""
import sqlite3
import sys

DB = r"D:\work\research\agents-nexus\data\reins.db"

# --- 1. Ensure table exists ---
print("=== Step 1: Ensure verification_task_log table ===")
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS verification_task_log (
    id TEXT PRIMARY KEY, task_id TEXT, agent_id TEXT,
    verifier_type TEXT, input_summary TEXT, output_raw TEXT,
    passed BOOLEAN, message TEXT, duration_seconds REAL,
    created_at TIMESTAMP DEFAULT (datetime('now'))
)""")
c.execute("CREATE INDEX IF NOT EXISTS idx_vlog_agent ON verification_task_log(agent_id)")
c.execute("CREATE INDEX IF NOT EXISTS idx_vlog_task ON verification_task_log(task_id)")
conn.commit()
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='verification_task_log'")
assert c.fetchone() is not None, "Table not found"
print("  OK: table exists")

# --- 2. Compile check (already done externally) ---
print("\n=== Step 2: py_compile check ===")
import py_compile
try:
    py_compile.compile(
        r"D:\work\research\agents-nexus\packages\server\src\reins\verifiers\ability_tracker.py",
        doraise=True,
    )
    print("  OK: 0 errors")
except py_compile.PyCompileError as e:
    print(f"  FAIL: {e}")
    sys.exit(1)

# --- 3. Test record() ---
print("\n=== Step 3: Test AbilityTracker.record() ===")
sys.path.insert(0, r"D:\work\research\agents-nexus\packages\server\src")
from reins.verifiers.ability_tracker import AbilityTracker

# Use the existing connection for testing
log_id1 = AbilityTracker.record(
    agent_id="test-agent-001",
    result=True,
    task_id="task-1",
    verifier_type="content_verifier",
    input_summary="test input",
    output_raw="test output",
    duration=1.5,
    db_session=conn,
)
print(f"  Inserted log_id: {log_id1}")

# Verify the row exists
c.execute("SELECT COUNT(*) FROM verification_task_log WHERE id = ?", (log_id1,))
assert c.fetchone()[0] == 1, "Record not found after insert"
print("  OK: record() writes to verification_task_log")

# Insert a few more for stats testing
AbilityTracker.record("test-agent-001", True, duration=2.0, db_session=conn)
AbilityTracker.record("test-agent-001", False, duration=3.0, db_session=conn)
AbilityTracker.record("test-agent-002", True, duration=0.5, db_session=conn)
print("  Inserted 3 more records")

# --- 4. Test get_agent_stats() ---
print("\n=== Step 4: Test AbilityTracker.get_agent_stats() ===")

stats = AbilityTracker.get_agent_stats("test-agent-001", db_session=conn)
print(f"  Stats for test-agent-001: {stats}")
assert stats["total"] == 3, f"Expected total=3, got {stats['total']}"
assert stats["passed"] == 2, f"Expected passed=2, got {stats['passed']}"
assert abs(stats["passed_rate"] - 0.6667) < 0.01, f"Expected passed_rate~0.6667, got {stats['passed_rate']}"
assert abs(stats["avg_duration"] - 2.1667) < 0.01, f"Expected avg_duration~2.1667, got {stats['avg_duration']}"
print("  OK: get_agent_stats() returns correct data")

stats2 = AbilityTracker.get_agent_stats("test-agent-002", db_session=conn)
print(f"  Stats for test-agent-002: {stats2}")
assert stats2["total"] == 1
assert stats2["passed"] == 1
assert stats2["passed_rate"] == 1.0
print("  OK: single-record stats correct")

stats_empty = AbilityTracker.get_agent_stats("nonexistent-agent", db_session=conn)
print(f"  Stats for nonexistent: {stats_empty}")
assert stats_empty["total"] == 0
assert stats_empty["passed"] == 0
assert stats_empty["passed_rate"] == 0.0
assert stats_empty["avg_duration"] == 0.0
print("  OK: empty agent returns zeros")

conn.close()

print("\n[OK] All tests passed!")
