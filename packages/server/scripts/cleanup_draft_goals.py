#!/usr/bin/env python3
"""
Script to cleanup orphan draft goals that have workflow_id but no projects/tasks.
These are garbage data from interrupted processes.
"""

import sqlite3
import sys
from pathlib import Path


def get_db_connection(db_path):
    """Create database connection with row factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def find_orphan_draft_goals(conn):
    """Find draft goals that have workflow_id but no associated projects AND no associated tasks."""
    query = """
    SELECT g.id, g.title, g.status, g.workflow_id, g.created_at
    FROM goals g
    WHERE g.status = 'draft' 
    AND g.workflow_id IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM projects p WHERE p.goal_id = g.id
    )
    AND NOT EXISTS (
        SELECT 1 FROM tasks t WHERE t.goal_id = g.id
    )
    """
    
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()


def count_workflow_data(conn, workflow_id):
    """Count associated workflow_steps for a given workflow_id."""
    cursor = conn.cursor()
    
    # Count workflow_steps
    cursor.execute("SELECT COUNT(*) FROM workflow_steps WHERE workflow_id = ?", (workflow_id,))
    step_count = cursor.fetchone()[0]
    
    return step_count


def preview_deletions(conn):
    """Preview what will be deleted."""
    orphan_goals = find_orphan_draft_goals(conn)
    
    print(f"Found {len(orphan_goals)} orphan draft goals to clean up:")
    print("-" * 80)
    
    total_steps_to_delete = 0
    
    for goal in orphan_goals:
        step_count = count_workflow_data(conn, goal['workflow_id'])
        total_steps_to_delete += step_count
        
        print(f"Goal ID: {goal['id']}")
        print(f"  Title: {goal['title'][:50]}{'...' if len(goal['title']) > 50 else ''}")
        print(f"  Status: {goal['status']}")
        print(f"  Workflow ID: {goal['workflow_id']}")
        print(f"  Created: {goal['created_at']}")
        print(f"  Associated workflow steps: {step_count}")
        print()
    
    print(f"Total orphan draft goals to delete: {len(orphan_goals)}")
    print(f"Total workflow steps to delete: {total_steps_to_delete}")
    
    # Get total counts for context
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM goals WHERE status = 'draft'")
    total_draft_goals = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM workflows")
    total_workflows = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM workflow_steps")
    total_steps = cursor.fetchone()[0]
    
    print(f"Total draft goals before cleanup: {total_draft_goals}")
    print(f"Total workflows before cleanup: {total_workflows}")
    print(f"Total workflow steps before cleanup: {total_steps}")
    
    return orphan_goals


def perform_cleanup(conn, orphan_goals):
    """Perform the actual deletion of orphan goals and associated data."""
    cursor = conn.cursor()
    
    deleted_goals = 0
    deleted_workflows = 0
    deleted_steps = 0
    
    for goal in orphan_goals:
        # Delete associated workflow_steps first
        cursor.execute("DELETE FROM workflow_steps WHERE workflow_id = ?", (goal['workflow_id'],))
        steps_deleted = cursor.rowcount
        deleted_steps += steps_deleted
        
        # Delete the workflow
        cursor.execute("DELETE FROM workflows WHERE id = ?", (goal['workflow_id'],))
        workflows_deleted = cursor.rowcount
        deleted_workflows += workflows_deleted
        
        # Finally delete the goal itself
        cursor.execute("DELETE FROM goals WHERE id = ?", (goal['id'],))
        goals_deleted = cursor.rowcount
        deleted_goals += goals_deleted
    
    conn.commit()
    
    print(f"\nCleanup completed!")
    print(f"- Deleted {deleted_goals} orphan draft goals")
    print(f"- Deleted {deleted_workflows} orphan workflows") 
    print(f"- Deleted {deleted_steps} orphan workflow steps")
    
    return deleted_goals, deleted_workflows, deleted_steps


def verify_cleanup(conn):
    """Verify that the cleanup worked correctly."""
    remaining_orphans = find_orphan_draft_goals(conn)
    
    print(f"\nVerification:")
    print(f"- Remaining orphan draft goals: {len(remaining_orphans)}")
    
    if len(remaining_orphans) == 0:
        print("Cleanup verification PASSED: No orphan draft goals remain")
        return True
    else:
        print("Cleanup verification FAILED: Some orphan draft goals still exist")
        return False


def main():
    db_path = "D:\\work\\research\\agents-nexus\\data\\reins.db"
    
    # Verify DB file exists
    if not Path(db_path).exists():
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)
    
    print(f"Connecting to database: {db_path}")
    
    conn = get_db_connection(db_path)
    
    try:
        # Preview what will be deleted
        orphan_goals = preview_deletions(conn)
        
        if not orphan_goals:
            print("\nNo orphan draft goals found. Nothing to clean up.")
            return
        
        # For automated execution, proceed without interactive confirmation
        print("\nAutomated execution: Proceeding with cleanup...")
        
        # Perform the cleanup
        print("\nStarting cleanup...")
        perform_cleanup(conn, orphan_goals)
        
        # Verify the cleanup
        success = verify_cleanup(conn)
        
        if success:
            print("\nAll cleanup tasks completed successfully!")
        else:
            print("\nSome issues were found during cleanup verification.")
    
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")
        conn.rollback()
        sys.exit(1)
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()