"""
Human Ruling E2E Test Task for goal-a697a85868a4

This test verifies the scenario where verification fails 3 times and triggers the disputed state.
"""

from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json
import uuid

from reins.common.database import get_db_manager
from src.reins.scheduler.result_verifier import ResultVerifier


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_human_ruling_a697a85868a4.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_verification_fails_3_times_triggers_disputed():
    """
    Test that verification failing 3 times triggers the disputed state for goal-a697a85868a4
    
    This test verifies the complete workflow:
    1. Create task with acceptance criteria
    2. First verification attempt fails (goes to review_needed)
    3. Second verification attempt fails (still review_needed)
    4. Third verification attempt fails (triggers disputed state)
    5. Verify task is in disputed state
    """
    print("\n" + "="*70)
    print("HUMAN RULING E2E TEST FOR GOAL-A697A85868A4")
    print("Test: Verification fails 3 times triggers disputed state")
    print("="*70)
    
    db_manager = get_db_manager()
    verifier = ResultVerifier(db_manager)
    
    try:
        # Setup test database
        db = TestingSessionLocal()
        
        # Create goal with specific ID for goal-a697a85868a4
        goal_id = "goal-a697a85868a4"
        
        # Check if goal exists, if not create it
        existing_goal = db.execute(text("SELECT id FROM goals WHERE id = :id"), {"id": goal_id}).fetchone()
        
        if not existing_goal:
            db.execute(text("""
                INSERT INTO goals (id, title, description, status, verifier_agent_id, created_at, updated_at)
                VALUES (:id, :title, :description, :status, :verifier_agent_id, :created_at, :updated_at)
            """), {
                "id": goal_id,
                "title": "Human Ruling Test Goal for A697A85868A4",
                "description": "Goal for testing disputed state trigger for goal-a697a85868a4",
                "status": "active",
                "verifier_agent_id": "human-ruling-verifier-a697a85868a4",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })
            db.commit()
            print(f"✓ Created goal: {goal_id}")
        else:
            print(f"✓ Goal {goal_id} already exists")
        
        # Create project
        project_id = f"proj-a697a85868a4-{uuid.uuid4().hex[:8]}"
        db.execute(text("""
            INSERT INTO projects (id, name, description, status, goal_id, created_at, updated_at, verifier_agent_id)
            VALUES (:id, :name, :description, :status, :goal_id, :created_at, :updated_at, NULL)
        """), {
            "id": project_id,
            "name": "Human Ruling Test Project for A697A85868A4",
            "description": "Project for testing disputed state for goal-a697a85868a4",
            "status": "active",
            "goal_id": goal_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })
        db.commit()
        print(f"✓ Created project: {project_id}")
        
        # Create task with acceptance criteria
        task_id = f"task-disputed-a697a85868a4-{uuid.uuid4().hex[:8]}"
        acceptance_criteria = {
            "criteria": [
                {
                    "type": "compile",
                    "name": "Compilation Check",
                    "desc": "Verify code compiles successfully for goal-a697a85868a4"
                },
                {
                    "type": "api",
                    "endpoint": "http://localhost:8090/api/v1/health",
                    "name": "API Health Check",
                    "desc": "Verify API is healthy for goal-a697a85868a4"
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
            "title": "Human Ruling Test Task for goal-a697a85868a4 - Will Trigger Disputed",
            "description": "This task will fail verification 3 times to trigger disputed state for goal-a697a85868a4",
            "status": "in_progress",
            "priority": "high",
            "project_id": project_id,
            "goal_id": goal_id,
            "assigned_agent": "test-agent-a697a85868a4",
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
            return False, "Verification failed - compilation error detected (mocked for goal-a697a85868a4)"
        
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
        """), {"task_id": task_id}).fetchone()
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
        
        # Restore original method
        verifier._run_verifier_checks = original_run_checks
        
        db.close()
        
        print("\n" + "="*70)
        print("✅ HUMAN RULING E2E TEST FOR GOAL-A697A85868A4 PASSED")
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
        print(f"\n❌ HUMAN RULING E2E TEST FOR GOAL-A697A85868A4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise e


def test_verification_passes_after_retry():
    """
    Test that if the third attempt passes, the task goes to done for goal-a697a85868a4
    """
    print("\n" + "="*70)
    print("HUMAN RULING E2E TEST - PASSES ON THIRD ATTEMPT FOR GOAL-A697A85868A4")
    print("="*70)
    
    db_manager = get_db_manager()
    verifier = ResultVerifier(db_manager)
    
    try:
        # Setup test database
        db = TestingSessionLocal()
        
        # Create goal for comparison test
        goal_id = "goal-a697a85868a4-pass"
        db.execute(text("""
            INSERT INTO goals (id, title, description, status, verifier_agent_id, created_at, updated_at)
            VALUES (:id, :title, :description, :status, :verifier_agent_id, :created_at, :updated_at)
        """), {
            "id": goal_id,
            "title": "Human Ruling Test Goal for A697A85868A4 - Pass",
            "description": "Goal for testing passing verification for goal-a697a85868a4",
            "status": "active",
            "verifier_agent_id": "human-ruling-verifier-a697a85868a4",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })
        
        # Create project
        project_id = f"proj-pass-a697a85868a4-{uuid.uuid4().hex[:8]}"
        db.execute(text("""
            INSERT INTO projects (id, name, description, status, goal_id, created_at, updated_at, verifier_agent_id)
            VALUES (:id, :name, :description, :status, :goal_id, :created_at, :updated_at, NULL)
        """), {
            "id": project_id,
            "name": "Human Ruling Test Project for A697A85868A4 - Pass",
            "description": "Project for testing passing verification for goal-a697a85868a4",
            "status": "active",
            "goal_id": goal_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })
        
        # Create task
        task_id = f"task-pass-a697a85868a4-{uuid.uuid4().hex[:8]}"
        db.execute(text("""
            INSERT INTO tasks (id, title, description, status, priority, project_id, goal_id, 
                            assigned_agent, verification_cycle, acceptance_criteria, created_at, updated_at, verifier_agent_id)
            VALUES (:id, :title, :description, :status, :priority, :project_id, :goal_id, 
                    :assigned_agent, :verification_cycle, :acceptance_criteria, :created_at, :updated_at, NULL)
        """), {
            "id": task_id,
            "title": "Human Ruling Test Task for goal-a697a85868a4 - Passes on Third",
            "description": "This task passes on third attempt for goal-a697a85868a4",
            "status": "in_progress",
            "priority": "high",
            "project_id": project_id,
            "goal_id": goal_id,
            "assigned_agent": "test-agent-a697a85868a4",
            "verification_cycle": 0,
            "acceptance_criteria": json.dumps({"criteria": [{"type": "compile", "name": "Check", "desc": "Verify for goal-a697a85868a4"}]}),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })
        db.commit()
        print(f"✓ Created task: {task_id}")
        
        # Mock: fail twice, then pass
        call_count = [0]
        def mock_fail_then_pass(task_id, result):
            call_count[0] += 1
            if call_count[0] < 3:
                return False, f"Verification failed (attempt {call_count[0]}) for goal-a697a85868a4"
            return True, "All checks passed on third attempt for goal-a697a85868a4"
        
        original_run_checks = verifier._run_verifier_checks
        verifier._run_verifier_checks = mock_fail_then_pass
        
        # First attempt (fail)
        result1 = verifier.verify(task_id, "Failed first attempt for goal-a697a85868a4", success=True)
        print(f"\n✓ First attempt: {result1['action']}")
        task_status = db.execute(text("SELECT status FROM tasks WHERE id = :id"), {"id": task_id}).fetchone()
        assert task_status[0] == "review_needed"
        
        # Second attempt (fail)
        result2 = verifier.verify(task_id, "Failed second attempt for goal-a697a85868a4", success=True)
        print(f"✓ Second attempt: {result2['action']}")
        task_status = db.execute(text("SELECT status FROM tasks WHERE id = :id"), {"id": task_id}).fetchone()
        assert task_status[0] == "review_needed"
        
        # Third attempt (pass!)
        result3 = verifier.verify(task_id, "Passed on third attempt for goal-a697a85868a4", success=True)
        print(f"✓ Third attempt: {result3['action']}")
        task_status = db.execute(text("SELECT status FROM tasks WHERE id = :id"), {"id": task_id}).fetchone()
        assert task_status[0] == "done", f"Expected 'done', got '{task_status[0]}'"
        
        # Restore original method
        verifier._run_verifier_checks = original_run_checks
        
        db.close()
        
        print("\n✅ Test passed: Task goes to done after third successful attempt for goal-a697a85868a4")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise e


if __name__ == "__main__":
    success = True
    
    # Run first test
    try:
        test_verification_fails_3_times_triggers_disputed()
        print("\n" + "="*70)
        print("TEST 1: FAILED 3 TIMES → DISPUTED FOR GOAL-A697A85868A4")
        print("="*70)
    except Exception as e:
        success = False
        print(f"\n❌ TEST 1 FAILED: {e}")
    
    # Run second test
    try:
        test_verification_passes_after_retry()
        print("\n" + "="*70)
        print("TEST 2: FAILS TWICE, PASSES THIRD → DONE FOR GOAL-A697A85868A4")
        print("="*70)
    except Exception as e:
        success = False
        print(f"\n❌ TEST 2 FAILED: {e}")
    
    if success:
        print("\n" + "="*70)
        print("🎉 ALL HUMAN RULING E2E TESTS FOR GOAL-A697A85868A4 PASSED!")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("❌ SOME TESTS FAILED FOR GOAL-A697A85868A4")
        print("="*70)
        exit(1)