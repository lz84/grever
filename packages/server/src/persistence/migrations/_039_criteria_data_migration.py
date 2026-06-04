"""
Migration 039 Data Migration: Parse description blocks and populate criteria columns.
- Extract ## Done Criteria checkbox items → done_criteria JSON
- Extract ## Acceptance Criteria JSON block → acceptance_criteria (if empty)
"""

import json
import re
import sqlite3
from pathlib import Path

DB_PATH = Path("D:/work/research/agents-nexus/data/reins.db")


def extract_done_criteria_from_markdown(text: str) -> list | None:
    """Parse ## Done Criteria checkbox block from markdown description."""
    pattern = r'##\s*Done\s*Criteria\s*\n([\s\S]*?)(?=##\s*[A-Z]|$)'
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None

    block = match.group(1).strip()
    items = []
    for line in block.split('\n'):
        line = line.strip()
        if not line.startswith('- ['):
            continue
        # Parse checkbox: - [ ] item text or - [x] item text
        checkbox_match = re.match(r'- \[[ xX]\]\s*(.*)', line)
        if checkbox_match:
            desc = checkbox_match.group(1).strip()
            if desc:
                items.append({
                    "type": "custom",
                    "name": "",
                    "desc": desc,
                })

    if not items:
        return None
    return {"criteria": items}


def extract_acceptance_criteria_from_markdown(text: str) -> dict | None:
    """Extract ## Acceptance Criteria JSON block from markdown description."""
    pattern = r'##\s*Acceptance\s*Criteria\s*\n([\s\S]*?)(?=##\s*[A-Z]|$)'
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None

    block = match.group(1).strip()
    # Try to parse as JSON
    try:
        parsed = json.loads(block)
        if isinstance(parsed, dict) and parsed.get('criteria'):
            return parsed
        elif isinstance(parsed, list):
            return {"criteria": parsed}
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def run_migration():
    if not DB_PATH.exists():
        print(f"数据库文件不存在: {DB_PATH}")
        return False

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        # Check if done_criteria column exists
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'done_criteria' not in columns:
            print("ERROR: done_criteria column does not exist. Run SQL migration first.")
            return False

        # Fetch all tasks with description
        cursor.execute("SELECT id, description, done_criteria, acceptance_criteria FROM tasks WHERE description IS NOT NULL AND description != ''")
        rows = cursor.fetchall()

        updated_done = 0
        updated_acceptance = 0

        for task_id, description, existing_done, existing_acceptance in rows:
            updates = {}

            # Extract done_criteria if not already set
            if not existing_done:
                done_data = extract_done_criteria_from_markdown(description)
                if done_data:
                    updates['done_criteria'] = json.dumps(done_data)

            # Extract acceptance_criteria if not already set
            if not existing_acceptance:
                ac_data = extract_acceptance_criteria_from_markdown(description)
                if ac_data:
                    updates['acceptance_criteria'] = json.dumps(ac_data)

            # Apply updates
            if updates:
                for key, value in updates.items():
                    cursor.execute(f"UPDATE tasks SET {key} = ? WHERE id = ?", (value, task_id))
                    if key == 'done_criteria':
                        updated_done += 1
                    elif key == 'acceptance_criteria':
                        updated_acceptance += 1

        conn.commit()
        print(f"Migration 039 data migration complete: {updated_done} done_criteria, {updated_acceptance} acceptance_criteria updated.")
        return True

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)
