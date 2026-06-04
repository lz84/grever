"""
Full Chain Test for Verifier Inheritance
Test: no Task verifier, no Project verifier, Goal has verifier
For goal-57ba66f6a233
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///.test_verifier_inheritance.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_verifier_inheritance_chain():
    """
    Test the full chain of verifier inheritance:
    Task without verifier -> Project without verifier -> Goal with verifier -> Uses goal's verifier
    
    This verifies the scenario: no Task verifier, no Project verifier, Goal has verifier
    """
    print("Testing Verifier Inheritance Chain...")
    print("Scenario: Task without verifier -> Project without verifier -> Goal with verifier")
    
    db = TestingSessionLocal()
    
    try:
        # 1. Create a Goal with a specific verifier agent
        goal_id = "goal-test-57ba66f6a233"
        goal_data = {
            "id": goal_id,
            "title": "Test Goal for Verifier Inheritance",
            "description": "Goal to test verifier inheritance chain",
            "status": "active",
            "verifier_agent_id": "feishu-verifier-agent",  # Goal has specific verifier
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.execute(text("""
            INSERT INTO goals (id, title, description, status, verifier_agent_id, created_at, updated_at)
            VALUES (:id, :title, :description, :status, :verifier_agent_id, :created_at, :updated_at)
        """), goal_data)
        
        print(f"✓ Created goal {goal_id} with verifier 'feishu-verifier-agent'")
        
        # 2. Create a Project without a verifier (should inherit from goal)
        project_id = "proj-test-57ba66f6a233"
        project_data = {
            "id": project_id,
            "name": "Test Project for Verifier Inheritance",
            "description": "Project to test verifier inheritance from goal",
            "status": "active",
            "goal_id": goal_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.execute(text("""
            INSERT INTO projects (id, name, description, status, goal_id, created_at, updated_at, verifier_agent_id)
            VALUES (:id, :name, :description, :status, :goal_id, :created_at, :updated_at, :verifier_agent_id)
        """), {
            "id": project_id,
            "name": project_data["name"],
            "description": project_data["description"],
            "status": project_data["status"],
            "goal_id": project_data["goal_id"],
            "created_at": project_data["created_at"],
            "updated_at": project_data["updated_at"],
            "verifier_agent_id": None  # Explicitly set to None
        })
        
        print(f"✓ Created project {project_id} without verifier (will inherit from goal)")
        
        # 3. Create a Task without a verifier (should inherit from project/goal)
        task_id = "task-test-57ba66f6a233"
        task_data = {
            "id": task_id,
            "title": "Test Task for Verifier Inheritance",
            "description": "Task to test verifier inheritance from goal through project",
            "status": "todo",
            "priority": "medium",
            "project_id": project_id,
            "goal_id": goal_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.execute(text("""
            INSERT INTO tasks 
            (id, title, description, status, priority, project_id, goal_id, created_at, updated_at, verifier_agent_id)
            VALUES (:id, :title, :description, :status, :priority, :project_id, :goal_id, :created_at, :updated_at, :verifier_agent_id)
        """), {
            "id": task_id,
            "title": task_data["title"],
            "description": task_data["description"],
            "status": task_data["status"],
            "priority": task_data["priority"],
            "project_id": task_data["project_id"],
            "goal_id": task_data["goal_id"],
            "created_at": task_data["created_at"],
            "updated_at": task_data["updated_at"],
            "verifier_agent_id": None  # Explicitly set to None
        })
        
        db.commit()
        print(f"✓ Created task {task_id} without verifier (will inherit from project/goal)")
        
        # 4. Test the inheritance mechanism using ResultVerifier
        from src.reins.scheduler.result_verifier import ResultVerifier
        verifier = ResultVerifier()
        
        # Test the resolve_effective_verifier method
        effective_verifier = verifier.resolve_effective_verifier(task_id)
        
        print(f"✓ Resolved effective verifier: {effective_verifier}")
        
        # 5. Verify that the task inherited the goal's verifier
        expected_verifier = "feishu-verifier-agent"
        assert effective_verifier == expected_verifier, f"Expected '{expected_verifier}', got '{effective_verifier}'"
        
        print(f"✅ SUCCESS: Task inherited verifier from goal as expected")
        print(f"   Task: {task_id}")
        print(f"   Task verifier: None (inherited)")
        print(f"   Project verifier: None (inherited)")
        print(f"   Goal verifier: {expected_verifier}")
        print(f"   Effective verifier: {effective_verifier}")
        
        # 6. Additional verification: check the inheritance path
        # Verify that the goal exists and has the correct verifier
        result = db.execute(text("SELECT verifier_agent_id FROM goals WHERE id = :id"), {"id": goal_id}).fetchone()
        assert result is not None, f"Goal {goal_id} not found"
        assert result[0] == expected_verifier, f"Goal has verifier '{result[0]}', expected '{expected_verifier}'"
        
        # Verify that the project has no verifier (NULL)
        result = db.execute(text("SELECT verifier_agent_id FROM projects WHERE id = :id"), {"id": project_id}).fetchone()
        assert result is not None, f"Project {project_id} not found"
        assert result[0] is None, f"Project should have NULL verifier, got '{result[0]}'"
        
        # Verify that the task has no verifier (NULL)
        result = db.execute(text("SELECT verifier_agent_id FROM tasks WHERE id = :id"), {"id": task_id}).fetchone()
        assert result is not None, f"Task {task_id} not found"
        assert result[0] is None, f"Task should have NULL verifier, got '{result[0]}'"
        
        print("✅ All inheritance chain verifications passed!")
        
        return {
            "task_id": task_id,
            "project_id": project_id,
            "goal_id": goal_id,
            "expected_verifier": expected_verifier,
            "actual_verifier": effective_verifier,
            "inheritance_works": effective_verifier == expected_verifier
        }
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()


def test_verifier_inheritance_priority():
    """
    Test that the verifier inheritance follows the correct priority:
    Task.verifier_agent_id > Project.verifier_agent_id > Goal.verifier_agent_id > DEFAULT
    """
    print("\nTesting Verifier Inheritance Priority...")
    
    db = TestingSessionLocal()
    
    try:
        # 1. Create a Goal with a verifier
        goal_id = "goal-priority-test-57ba66f6a233"
        goal_data = {
            "id": goal_id,
            "title": "Priority Test Goal",
            "description": "Goal for testing inheritance priority",
            "status": "active",
            "verifier_agent_id": "goal-default-verifier",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.execute(text("""
            INSERT INTO goals (id, title, description, status, verifier_agent_id, created_at, updated_at)
            VALUES (:id, :title, :description, :status, :verifier_agent_id, :created_at, :updated_at)
        """), goal_data)
        
        # 2. Create a Project with a verifier (higher priority than goal)
        project_id = "proj-priority-test-57ba66f6a233"
        project_data = {
            "id": project_id,
            "name": "Priority Test Project",
            "description": "Project with specific verifier",
            "status": "active",
            "goal_id": goal_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.execute(text("""
            INSERT INTO projects (id, name, description, status, goal_id, created_at, updated_at, verifier_agent_id)
            VALUES (:id, :name, :description, :status, :goal_id, :created_at, :updated_at, :verifier_agent_id)
        """), {
            "id": project_id,
            "name": project_data["name"],
            "description": project_data["description"],
            "status": project_data["status"],
            "goal_id": project_data["goal_id"],
            "created_at": project_data["created_at"],
            "updated_at": project_data["updated_at"],
            "verifier_agent_id": "project-specific-verifier"  # Higher priority than goal
        })
        
        # 3. Create a Task WITHOUT a verifier (should inherit from project)
        task_without_verifier_id = "task-no-verifier-priority-57ba66f6a233"
        task_data = {
            "id": task_without_verifier_id,
            "title": "Task Without Verifier",
            "description": "Task without specific verifier (inherits from project)",
            "status": "todo",
            "priority": "medium",
            "project_id": project_id,
            "goal_id": goal_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.execute(text("""
            INSERT INTO tasks 
            (id, title, description, status, priority, project_id, goal_id, created_at, updated_at, verifier_agent_id)
            VALUES (:id, :title, :description, :status, :priority, :project_id, :goal_id, :created_at, :updated_at, :verifier_agent_id)
        """), {
            "id": task_without_verifier_id,
            "title": task_data["title"],
            "description": task_data["description"],
            "status": task_data["status"],
            "priority": task_data["priority"],
            "project_id": task_data["project_id"],
            "goal_id": task_data["goal_id"],
            "created_at": task_data["created_at"],
            "updated_at": task_data["updated_at"],
            "verifier_agent_id": None  # No verifier - should inherit from project
        })
        
        # 4. Create a Task WITH a verifier (highest priority)
        task_with_verifier_id = "task-with-verifier-priority-57ba66f6a233"
        task_with_verifier_data = {
            "id": task_with_verifier_id,
            "title": "Task With Verifier",
            "description": "Task with specific verifier (highest priority)",
            "status": "todo",
            "priority": "medium",
            "project_id": project_id,
            "goal_id": goal_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.execute(text("""
            INSERT INTO tasks 
            (id, title, description, status, priority, project_id, goal_id, verifier_agent_id, created_at, updated_at)
            VALUES (:id, :title, :description, :status, :priority, :project_id, :goal_id, :verifier_agent_id, :created_at, :updated_at)
        """), {
            "id": task_with_verifier_id,
            "title": task_with_verifier_data["title"],
            "description": task_with_verifier_data["description"],
            "status": task_with_verifier_data["status"],
            "priority": task_with_verifier_data["priority"],
            "project_id": task_with_verifier_data["project_id"],
            "goal_id": task_with_verifier_data["goal_id"],
            "verifier_agent_id": "task-specific-verifier",  # Highest priority
            "created_at": task_with_verifier_data["created_at"],
            "updated_at": task_with_verifier_data["updated_at"]
        })
        
        db.commit()
        
        print("✓ Created test data with different verifier priorities")
        
        # 5. Test inheritance priority using ResultVerifier
        from src.reins.scheduler.result_verifier import ResultVerifier
        verifier = ResultVerifier()
        
        # Test task without verifier inherits from project
        effective_verifier_no_verifier = verifier.resolve_effective_verifier(task_without_verifier_id)
        print(f"✓ Task without verifier gets: {effective_verifier_no_verifier}")
        assert effective_verifier_no_verifier == "project-specific-verifier", f"Expected project verifier, got {effective_verifier_no_verifier}"
        
        # Test task with verifier uses its own
        effective_verifier_with_verifier = verifier.resolve_effective_verifier(task_with_verifier_id)
        print(f"✓ Task with verifier gets: {effective_verifier_with_verifier}")
        assert effective_verifier_with_verifier == "task-specific-verifier", f"Expected task verifier, got {effective_verifier_with_verifier}"
        
        print("✅ Verifier inheritance priority test passed!")
        print("   Task.verifier > Project.verifier > Goal.verifier > DEFAULT")
        
        return True
        
    except Exception as e:
        print(f"❌ Priority test failed: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        db.close()


def run_tests():
    """
    Run all verifier inheritance tests
    """
    print("=" * 70)
    print("VERIFIER INHERITANCE CHAIN TEST")
    print("Goal: goal-57ba66f6a233")
    print("Test: no Task verifier, no Project verifier, Goal has verifier")
    print("=" * 70)
    
    success_count = 0
    total_tests = 2
    
    try:
        # Test 1: Basic inheritance chain (the main scenario)
        result1 = test_verifier_inheritance_chain()
        if result1["inheritance_works"]:
            success_count += 1
            print(f"\n✅ Test 1 PASSED: Basic inheritance chain")
        else:
            print(f"\n❌ Test 1 FAILED: Basic inheritance chain")
    except Exception as e:
        print(f"\n❌ Test 1 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        # Test 2: Priority verification
        test_verifier_inheritance_priority()
        success_count += 1
        print(f"✅ Test 2 PASSED: Inheritance priority")
    except Exception as e:
        print(f"❌ Test 2 FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {success_count}")
    print(f"Failed: {total_tests - success_count}")
    
    if success_count == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Verifier inheritance chain works correctly")
        print("✅ Priority order: Task > Project > Goal > DEFAULT")
        print("✅ Scenario 'no Task verifier, no Project verifier, Goal has verifier' verified")
        print("=" * 70)
        return True
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)