"""
E2E Verifier Test for goal-7c93b8c64c07

This test is specific to goal-7c93b8c64c07 and verifies the complete verification cycle.
The actual test logic is the same as test_e2e_verification_cycle.py but with goal-specific data.
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json
import uuid

from reins.common.database import get_db_manager
from src.reins.scheduler.result_verifier import ResultVerifier


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_e2e_verification_7c93b8c64c07.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_e2e_verification_for_goal_7c93b8c64c07():
    """
    E2E Test for goal-7c93b8c64c07 verification cycle
    """
    print("\n" + "="*70)
    print("E2E VERIFICATION TEST FOR GOAL-7C93B8C64C07")
    print("="*70)
    
    db_manager = get_db_manager()
    verifier = ResultVerifier(db_manager)
    
    try:
        # Setup test database
        db = TestingSessionLocal()
        
        # Create goal with specific ID for this test
        goal_id = "goal-7c93b8c64c07"
        
        # Check if goal exists, if not create it
        existing_goal = db.execute(text("SELECT id FROM goals WHERE id = :id"), {"id": goal_id}).fetchone()
        
        if not existing_goal:
            db.execute(text("""
                INSERT INTO goals (id, title, description, status, verifier_agent_id, created_at, updated_at)
                VALUES (:id, :title, :description, :status, :verifier_agent_id, :created_at, :updated_at)
            """), {
                "id": goal_id,
                "title": "E2E Test Goal 7c93b8c64c07",
                "description": "Goal for E2E verification testing specific to goal-7c93b8c64c07",
                "status": "active",
                "verifier_agent_id": "test-verifier-agent-7c93b8c64c07",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })
            db.commit()
            print(f"✓ Created goal: {goal_id}")
        else:
            print(f"✓ Goal {goal_id} already exists")
        
        # Create project
        project_id = f"proj-7c93b8c64c07-{uuid.uuid4().hex[:8]}"
        db.execute(text("""
            INSERT INTO projects (id, name, description, status, goal_id, created_at, updated_at, verifier_agent_id)
            VALUES (:id, :name, :description, :status, :goal_id, :created_at, :updated_at, NULL)
        """), {
            "id": project_id,
            "name": "Test Project for Goal 7c93b8c64c07",
            "description": "Project for E2E verification testing",
            "status": "active",
            "goal_id": goal_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })
        db.commit()
        print(f"✓ Created project: {project_id}")
        
        # Create task
        task_id = f"task-7c93b8c64c07-{uuid.uuid4().hex[:8]}"
        acceptance_criteria = {
            "criteria": [
                {
                    "type": "compile",
                    "name": "Compilation Check",
                    "desc": "Verify code compiles successfully"
                }
            ]
        }
        
        db.execute(text("""
            INSERT INTO tasks (id, title, description, status, priority, project_id, goal_id, 
                            assigned_agent, verification_cycle, acceptance_criteria, created_at, updated_at, verifier_agent_id)
            VALUES (:id, :title, :description, :status, :priority, :project_id, :goal_id, 
                    :assigned_agent, :verification_cycle, :acceptance_criteria, :created_at, :updated_at, NULL)
        """), {
            "id": task_id,
            "title": "E2E Test Task for Goal 7c93b8c64c07",
            "description": "Task for E2E verification testing specific to goal-7c93b8c64c07",
            "status": "in_progress",
            "priority": "high",
            "project_id": project_id,
            "goal_id": goal_id,
            "assigned_agent": "test-agent",
            "verification_cycle": 0,
            "acceptance_criteria": json.dumps(acceptance_criteria),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })
        db.commit()
        print(f"✓ Created task: {task_id}")
        
        # Test verifier inheritance
        effective_verifier = verifier.resolve_effective_verifier(task_id)
        print(f"\n✓ Resolved effective verifier: {effective_verifier}")
        assert effective_verifier == "test-verifier-agent-7c93b8c64c07", f"Expected goal-specific verifier"
        
        # Mock verification to pass
        original_run_checks = verifier._run_verifier_checks
        def mock_run_checks(task_id, result):
            return True, "All checks passed (mocked for goal-7c93b8c64c07)"
        verifier._run_verifier_checks = mock_run_checks
        
        # Trigger verification
        verification_result = verifier.verify(task_id, "Task completed successfully", success=True)
        
        print(f"\n✓ Verification triggered")
        print(f"  - Passed: {verification_result['passed']}")
        print(f"  - Action: {verification_result['action']}")
        print(f"  - Verifier: {verification_result['verifier_agent']}")
        
        # Verify task went to done
        task_status = db.execute(text("SELECT status FROM tasks WHERE id = :id"), {"id": task_id}).fetchone()
        print(f"\n✓ Task status: {task_status[0]}")
        assert task_status[0] == "done", f"Expected 'done', got '{task_status[0]}'"
        
        db.close()
        
        print("\n✅ E2E VERIFICATION TEST FOR GOAL-7C93B8C64C07 PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ E2E verification test FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise e


if __name__ == "__main__":
    success = test_e2e_verification_for_goal_7c93b8c64c07()
    exit(0 if success else 1)