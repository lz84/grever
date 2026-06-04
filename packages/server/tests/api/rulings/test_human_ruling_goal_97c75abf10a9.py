"""
Human Ruling E2E Test Task for goal-97c75abf10a9

This test verifies the scenario where verification fails 3 times and triggers the disputed state.
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
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_human_ruling_97c75abf10a9.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_verification_fails_3_times_triggers_disputed():
    """
    Test that verification failing 3 times triggers the disputed state for goal-97c75abf10a9
    """
    print("\n" + "="*70)
    print("HUMAN RULING E2E TEST FOR GOAL-97C75ABF10A9")
    print("Test: Verification fails 3 times triggers disputed state")
    print("="*70)
    
    db_manager = get_db_manager()
    verifier = ResultVerifier(db_manager)
    
    try:
        # Setup test database
        db = TestingSessionLocal()
        
        # Create goal with specific ID for goal-97c75abf10a9
        goal_id = "goal-97c75abf10a9"
        
        # Check if goal exists, if not create it
        existing_goal = db.execute(text("SELECT id FROM goals WHERE id = :id"), {"id": goal_id}).fetchone()
        
        if not existing_goal:
            db.execute(text("""
                INSERT INTO goals (id, title, description, status, verifier_agent_id, created_at, updated_at)
                VALUES (:id, :title, :description, :status, :verifier_agent_id, :created_at, :updated_at)
            """), {
                "id": goal_id,
                "title": "Human Ruling Test Goal 97c75abf10a9",
                "description": "Goal for testing disputed state trigger for goal-97c75abf10a9",
                "status": "active",
                "verifier_agent_id": "human-ruling-verifier-97c75abf10a9",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })
            db.commit()
            print(f"✓ Created goal: {goal_id}")
        else:
            print(f"✓ Goal {goal_id} already exists")
        
        # Create project
        project_id = f"proj-97c75abf10a9-{uuid.uuid4().hex[:8]}"
        db.execute(text("""
            INSERT INTO projects (id, name, description, status, goal_id, created_at, updated_at, verifier_agent_id)
            VALUES (:id, :name, :description, :status, :goal_id, :created_at, :updated_at, NULL)
        """), {
            "id": project_id,
            "name": "Human Ruling Test Project for 97c75abf10a9",
            "description": "Project for testing disputed state",
            "status": "active",
            "goal_id": goal_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })
        db.commit()
        print(f"✓ Created project: {project_id}")
        
        # Create task with acceptance criteria
        task_id = f"task-97c75abf10a9-{uuid.uuid4().hex[:8]}"
        acceptance_criteria = {
            "criteria": [
                {
                    "type": "compile",
                    "name": "Compilation Check",
                    "desc": "Verify code compiles successfully"
                },
                {
                    "type": "api",
                    "endpoint": "http://localhost:8090/api/v1/health",
                    "name": "API Health Check",
                    "desc": "Verify API is healthy"
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
            "title": "Human Ruling Test Task for 97c75abf10a9 - Will Trigger Disputed",
            "description": "This task will fail verification 3 times to trigger disputed state",
            "status": "in_progress",
            "priority": "high",
            "project_id": project_id,
            "goal_id": goal_id,
            "assigned_agent": "test-agent-97c75abf10a9",
            "verification_cycle": 0,
            "acceptance_criteria": json.dumps(acceptance_criteria),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })
        db.commit()
        print(f"✓ Created task: {task_id}")
        print(f"  - Task will fail verification 3 times")
        print(f"  - Should trigger disputed state after 3 failures")
        
        # Mock verification to always fail
        original_run_checks = verifier._run_verifier_checks
        
        def mock_run_checks_always_fail(task_id, result):
            # Always fail verification
            return False, "Verification failed - compilation error detected (mocked for goal-97c75abf10a9)"
        
        verifier._run_verifier_checks = mock_run_checks_always_fail
        
        # First verification attempt (should fail, go to review_needed)
        print(f"\n✓ FIRST VERIFICATION ATTEMPT")
        print(f"  Expected: Task goes to 'review_needed' status")
        
        result1 = verifier.verify(task_id, "Task completed but checks failed", success=True)
        
        print(f"  - Passed: {result1['passed']}")
        print(f"  - Action: {result1['action']}")
        print(f"  - Verification Cycle: {result1['verification_cycle']}")
        
        task_status = db.execute(text("SELECT status, verification_cycle FROM tasks WHERE id = :id"), {"id": task_id}).fetchone()
        print(f"  - Task Status: {task_status[0]}")
        print(f"  - Verification Cycle: {task_status[1]}")
        
        assert task_status[0] == "review_needed", f"Expected 'review_needed', got '{task_status[0]}'"
        assert task_status[1] == 1, f"Expected verification_cycle=1, got {task_status[1]}"
        print(f"  ✅ Status correctly changed to 'review_needed'")
        
        # Second verification attempt (should fail again, still review_needed)
        print(f"\n✓ SECOND VERIFICATION ATTEMPT")
        print(f"  Expected: Task still in 'review_needed' status")
        
        result2 = verifier.verify(task_id, "Task fixed but checks still fail", success=True)
        
        print(f"  - Passed: {result2['passed']}")
        print(f"  - Action: {result2['action']}")
        print(f"  - Verification Cycle: {result2['verification_cycle']}")
        
        task_status = db.execute(text("SELECT status, verification_cycle FROM tasks WHERE id = :id"), {"id": task_id}).fetchone()
        print(f"  - Task Status: {task_status[0]}")
        print(f"  - Verification Cycle: {task_status[1]}")
        
        assert task_status[0] == "review_needed", f"Expected 'review_needed', got '{task_status[0]}'"
        assert task_status[1] == 2, f"Expected verification_cycle=2, got {task_status[1]}"
        print(f"  ✅ Status correctly still in 'review_needed'")
        
        # Third verification attempt (should fail, trigger disputed state)
        print(f"\n✓ THIRD VERIFICATION ATTEMPT")
        print(f"  Expected: Task goes to 'disputed' status (max cycles reached)")
        
        result3 = verifier.verify(task_id, "Task still failing checks - max retries reached", success=True)
        
        print(f"  - Passed: {result3['passed']}")
        print(f"  - Action: {result3['action']}")
        print(f"  - Verification Cycle: {result3['verification_cycle']}")
        
        task_status = db.execute(text("SELECT status, verification_cycle FROM tasks WHERE id = :id"), {"id": task_id}).fetchone()
        print(f"  - Task Status: {task_status[0]}")
        print(f"  - Verification Cycle: {task_status[1]}")
        
        # This should trigger disputed state after 3 failures
        assert task_status[0] == "disputed", f"Expected 'disputed', got '{task_status[0]}'"
        assert task_status[1] == 3, f"Expected verification_cycle=3, got {task_status[1]}"
        print(f"  ✅ Status correctly changed to 'disputed' after 3 failures")
        
        # Verify verification comments
        comments = db.execute(text("""
            SELECT COUNT(*) FROM task_comments 
            WHERE task_id = :task_id AND type = 'verification'
        """), {"id": task_id}).fetchone()
        print(f"\n✓ Total verification comments: {comments[0]}")
        assert comments[0] == 3, f"Expected 3 verification comments, got {comments[0]}"
        
        # Verify the disputed state details
        disputed_info = db.execute(text("""
            SELECT status, verification_cycle, result_summary
            FROM tasks
            WHERE id = :id
        """), {"id": task_id}).fetchone()
        
        print(f"\n✓ FINAL TASK STATE:")
        print(f"  - Status: {disputed_info[0]}")
        print(f"  - Verification Cycle: {disputed_info[1]}")
        print(f"  - Result: {disputed_info[2]}")
        
        db.close()
        
        print("\n" + "="*70)
        print("✅ HUMAN RULING E2E TEST FOR GOAL-97C75ABF10A9 PASSED")
        print("="*70)
        print("Summary:")
        print("  ✓ First verification failed → review_needed")
        print("  ✓ Second verification failed → review_needed")
        print("  ✓ Third verification failed → DISPUTED")
        print("  ✓ Verification cycle reached maximum (3)")
        print("  ✓ Task correctly in disputed state")
        print("  ✓ Human ruling now required")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ HUMAN RULING E2E TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise e


if __name__ == "__main__":
    success = test_verification_fails_3_times_triggers_disputed()
    exit(0 if success else 1)