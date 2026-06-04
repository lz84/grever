"""
Migration 028: Data migration for capability tag system.
Converts Agent capabilities array → capability_tags JSON object.

Run AFTER 028_capability_tag_system.sql has been applied.
"""

import sqlite3
import json
import sys
import os

DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..", "..", "..", "data", "reins.db"
)
DB_PATH = os.path.normpath(DB_PATH)


def main():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if capability_tags column exists in agents table
    cursor.execute("PRAGMA table_info(agents)")
    columns = [r[1] for r in cursor.fetchall()]

    if "capability_tags" not in columns:
        print("ERROR: capability_tags column not found in agents table.")
        print("Please run 028_capability_tag_system.sql first.")
        sys.exit(1)

    if "capabilities" in columns:
        print("ERROR: Old 'capabilities' column still exists. RENAME COLUMN failed?")
        sys.exit(1)

    # Read all agents
    cursor.execute("SELECT id, capability_tags FROM agents")
    rows = cursor.fetchall()

    migrated = 0
    for agent_id, raw_value in rows:
        if not raw_value:
            # Already empty/null, set to default object
            cursor.execute(
                "UPDATE agents SET capability_tags = ? WHERE id = ?",
                (json.dumps({
                    "business": [],
                    "professional": [],
                    "technical": [],
                    "management": []
                }), agent_id)
            )
            migrated += 1
            continue

        try:
            data = json.loads(raw_value)
        except (json.JSONDecodeError, TypeError):
            print(f"  WARN: Invalid JSON for agent {agent_id}, resetting to default")
            cursor.execute(
                "UPDATE agents SET capability_tags = ? WHERE id = ?",
                (json.dumps({
                    "business": [],
                    "professional": [],
                    "technical": [],
                    "management": []
                }), agent_id)
            )
            migrated += 1
            continue

        # If already the new format (dict/object), skip
        if isinstance(data, dict) and set(data.keys()) & {"business", "professional", "technical", "management"}:
            print(f"  Agent {agent_id}: already in new format, skipping")
            continue

        # Old format: array of strings → convert to new object format
        if isinstance(data, list):
            new_format = {
                "business": [],
                "professional": [],
                "technical": data,  # All old capabilities go to technical
                "management": []
            }
            cursor.execute(
                "UPDATE agents SET capability_tags = ? WHERE id = ?",
                (json.dumps(new_format), agent_id)
            )
            migrated += 1
            print(f"  Agent {agent_id}: migrated {len(data)} tags → technical dimension")
        else:
            print(f"  WARN: Unexpected format for agent {agent_id}: {type(data)}, resetting")
            cursor.execute(
                "UPDATE agents SET capability_tags = ? WHERE id = ?",
                (json.dumps({
                    "business": [],
                    "professional": [],
                    "technical": [],
                    "management": []
                }), agent_id)
            )
            migrated += 1

    conn.commit()
    print(f"\nMigration complete: {migrated} agent(s) updated.")

    # Verify
    cursor.execute("SELECT id, capability_tags FROM agents LIMIT 5")
    for agent_id, tags in cursor.fetchall():
        parsed = json.loads(tags) if tags else {}
        dims = list(parsed.keys()) if isinstance(parsed, dict) else "INVALID"
        print(f"  {agent_id}: {dims}")

    conn.close()


if __name__ == "__main__":
    main()
