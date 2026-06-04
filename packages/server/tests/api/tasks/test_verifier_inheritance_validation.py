"""
Verification test for the three-level verifier inheritance mechanism
Task without verifier -> Project without verifier -> Goal with verifier
For goal-cb4c76143b4c
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json
import uuid


def test_verifier_inheritance_chain():
    """
    Test the three-level verifier inheritance chain:
    Task.verifier_agent_id > Project.verifier_agent_id > Goal.verifier_agent_id > DEFAULT
    """
    print("\n" + "="*70)
    print("TESTING VERIFIER INHERITANCE CHAIN")
    print("Goal: goal-cb4c76143b4c")
    print("Test: Task without verifier -> Project without verifier -> Goal with verifier")
    print("="*70)
    
    # Create test database
    SQLALCHEMY_DATABASE_URL = "sqlite:///./test_verifier_inheritance_validation.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    try:
        # 1. Create a Goal with a specific verifier agent
        goal_id = "goal-cb4c76143b4c"
        goal_data = {
            "id": goal_id,
            "title": "Test Goal for Verifier Inheritance Validation",
            "description": "Goal for testing three-level verifier inheritance",
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
        project_id = f"proj-{uuid.uuid4().hex[:12]}"
        project_data = {
            "id": project_id,
            "name": "Test Project for Verifier Inheritance Validation",
            "description": "Project for testing verifier inheritance from goal",
            "status": "active",
            "goal_id": goal_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
            # No verifier_agent_id specified - should inherit from goal
        }
        
        db.execute(text("""
            INSERT INTO projects (id, name, description, status, goal_id, created_at, updated_at, verifier_agent_id)
            VALUES (:id, :name, :description, :status, :goal_id, :created_at, :updated_at, NULL)
        """), {
            "id": project_id,
            "name": project_data["name"],
            "description": project_data["description"],
            "status": project_data["status"],
            "goal_id": project_data["goal_id"],
            "created_at": project_data["created_at"],
            "updated_at": project_data["updated_at"]
        })
        
        db.commit()
        print(f"✓ Created project {project_id} without verifier (will inherit from goal)")
        
        # 3. Create a Task without a verifier (should inherit from project/goal)
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        task_data = {
            "id": task_id,
            "title": "Test Task for Verifier Inheritance Validation",
            "description": "Task for testing verifier inheritance from goal",
            "status": "todo",
            "priority": "medium",
            "project_id": project_id,
            "goal_id": goal_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
            # No verifier_agent_id specified - should inherit from project/goal
        }
        
        db.execute(text("""
            INSERT INTO tasks 
            (id, title, description, status, priority, project_id, goal_id, created_at, updated_at, verifier_agent_id)
            VALUES (:id, :title, :description, :status, :priority, :project_id, :goal_id, :created_at, :updated_at, NULL)
        """), {
            "id": task_id,
            "title": task_data["title"],
            "description": task_data["description"],
            "status": task_data["status"],
            "priority": task_data["priority"],
            "project_id": task_data["project_id"],
            "goal_id": task_data["goal_id"],
            "created_at": task_data["created_at"],
            "updated_at": task_data["updated_at"]
        })
        
        db.commit()
        print(f"✓ Created task {task_id} without verifier (will inherit from project/goal)")
        
        # 4. Verify the inheritance mechanism using ResultVerifier
        from src.reins.scheduler.result_verifier import ResultVerifier
        verifier = ResultVerifier()
        
        # Temporarily override the db manager to use our test database
        original_db = verifier.db
        verifier.db = type('MockDB', (), {
            'engine': engine
        })()
        
        # Test the resolve_effective_verifier method
        effective_verifier = verifier.resolve_effective_verifier(task_id)
        
        print(f"✓ Resolved effective verifier: {effective_verifier}")
        
        # 5. Verify that the task inherited the goal's verifier
        expected_verifier = "feishu-verifier-agent"
        assert effective_verifier == expected_verifier, f"Expected '{expected_verifier}', got '{effective_verifier}'"
        
        print(f"\n✅ VERIFICATION SUCCESSFUL!")
        print(f"Task {task_id} correctly inherited verifier from goal:")
        print(f"  - Task verifier: None (inherited)")
        print(f"  - Project verifier: None (inherited)") 
        print(f"  - Goal verifier: {expected_verifier}")
        print(f"  - Effective verifier: {effective_verifier}")
        
        # 6. Additional validation: Check the database records
        print(f"\n6. Validating database records...")
        
        # Verify goal has the correct verifier
        goal_result = db.execute(text("SELECT verifier_agent_id FROM goals WHERE id = :id"), {"id": goal_id}).fetchone()
        assert goal_result[0] == expected_verifier, f"Goal should have verifier '{expected_verifier}', got '{goal_result[0]}'"
        print(f"   ✓ Goal {goal_id} has correct verifier: {goal_result[0]}")
        
        # Verify project has no verifier (NULL)
        project_result = db.execute(text("SELECT verifier_agent_id FROM projects WHERE id = :id"), {"id": project_id}).fetchone()
        assert project_result[0] is None, f"Project should have NULL verifier, got '{project_result[0]}'"
        print(f"   ✓ Project {project_id} has NULL verifier: {project_result[0]}")
        
        # Verify task has no verifier (NULL)
        task_result = db.execute(text("SELECT verifier_agent_id FROM tasks WHERE id = :id"), {"id": task_id}).fetchone()
        assert task_result[0] is None, f"Task should have NULL verifier, got '{task_result[0]}'"
        print(f"   ✓ Task {task_id} has NULL verifier: {task_result[0]}")
        
        # 7. Test with a task that has its own verifier (should take precedence)
        print(f"\n7. Testing task-level verifier precedence...")
        
        task_with_verifier_id = f"task-with-verifier-{uuid.uuid4().hex[:12]}"
        task_with_verifier_data = {
            "id": task_with_verifier_id,
            "title": "Test Task with Own Verifier",
            "description": "Task with its own verifier (should take precedence)",
            "status": "todo",
            "priority": "medium",
            "project_id": project_id,
            "goal_id": goal_id,
            "verifier_agent_id": "task-specific-verifier",  # Task has its own verifier
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
            "verifier_agent_id": task_with_verifier_data["verifier_agent_id"],
            "created_at": task_with_verifier_data["created_at"],
            "updated_at": task_with_verifier_data["updated_at"]
        })
        
        db.commit()
        
        # Test that task-level verifier takes precedence
        effective_verifier_task_specific = verifier.resolve_effective_verifier(task_with_verifier_id)
        assert effective_verifier_task_specific == "task-specific-verifier", f"Expected task-specific verifier, got '{effective_verifier_task_specific}'"
        print(f"   ✓ Task with own verifier correctly uses its own: {effective_verifier_task_specific}")
        
        # 8. Test with a project that has its own verifier (should take precedence over goal)
        print(f"\n8. Testing project-level verifier precedence...")
        
        project_with_verifier_id = f"proj-with-verifier-{uuid.uuid4().hex[:12]}"
        project_with_verifier_data = {
            "id": project_with_verifier_id,
            "name": "Test Project with Own Verifier",
            "description": "Project with its own verifier (should take precedence over goal)",
            "status": "active",
            "goal_id": goal_id,
            "verifier_agent_id": "project-specific-verifier",  # Project has its own verifier
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.execute(text("""
            INSERT INTO projects 
            (id, name, description, status, goal_id, verifier_agent_id, created_at, updated_at)
            VALUES (:id, :name, :description, :status, :goal_id, :verifier_agent_id, :created_at, :updated_at)
        """), {
            "id": project_with_verifier_id,
            "name": project_with_verifier_data["name"],
            "description": project_with_verifier_data["description"],
            "status": project_with_verifier_data["status"],
            "goal_id": project_with_verifier_data["goal_id"],
            "verifier_agent_id": project_with_verifier_data["verifier_agent_id"],
            "created_at": project_with_verifier_data["created_at"],
            "updated_at": project_with_verifier_data["updated_at"]
        })
        
        # Create a task under this project (no task-level verifier)
        task_under_project_with_verifier_id = f"task-under-proj-{uuid.uuid4().hex[:12]}"
        task_under_project_data = {
            "id": task_under_project_with_verifier_id,
            "title": "Task Under Project with Verifier",
            "description": "Task under project with verifier (should inherit from project)",
            "status": "todo",
            "priority": "medium",
            "project_id": project_with_verifier_id,
            "goal_id": goal_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
            # No verifier_agent_id - should inherit from project
        }
        
        db.execute(text("""
            INSERT INTO tasks 
            (id, title, description, status, priority, project_id, goal_id, created_at, updated_at, verifier_agent_id)
            VALUES (:id, :title, :description, :status, :priority, :project_id, :goal_id, :created_at, :updated_at, NULL)
        """), {
            "id": task_under_project_with_verifier_id,
            "title": task_under_project_data["title"],
            "description": task_under_project_data["description"],
            "status": task_under_project_data["status"],
            "priority": task_under_project_data["priority"],
            "project_id": task_under_project_data["project_id"],
            "goal_id": task_under_project_data["goal_id"],
            "created_at": task_under_project_data["created_at"],
            "updated_at": task_under_project_data["updated_at"]
        })
        
        db.commit()
        
        # Test that project-level verifier takes precedence over goal
        effective_verifier_project_specific = verifier.resolve_effective_verifier(task_under_project_with_verifier_id)
        assert effective_verifier_project_specific == "project-specific-verifier", f"Expected project-specific verifier, got '{effective_verifier_project_specific}'"
        print(f"   ✓ Task under project with verifier correctly inherits project's: {effective_verifier_project_specific}")
        
        # Restore original db
        verifier.db = original_db
        
        db.close()
        
        print(f"\n" + "="*70)
        print(f"✅ VERIFIER INHERITANCE VALIDATION COMPLETE!")
        print(f"="*70)
        print(f"✓ Task without verifier inherits from goal: {effective_verifier}")
        print(f"✓ Task with own verifier uses task-specific: task-specific-verifier") 
        print(f"✓ Task under project with verifier inherits from project: project-specific-verifier")
        print(f"✓ Inheritance priority: Task > Project > Goal > DEFAULT")
        print(f"✓ All validations passed for goal-cb4c76143b4c")
        print(f"="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ VERIFIER INHERITANCE VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        db.close()
        raise e


def test_verifier_inheritance_edge_cases():
    """
    Test edge cases for verifier inheritance
    """
    print("\n" + "="*50)
    print("TESTING VERIFIER INHERITANCE EDGE CASES")
    print("="*50)
    
    # Create test database
    SQLALCHEMY_DATABASE_URL = "sqlite:///./test_verifier_inheritance_edge_cases.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    try:
        # 1. Test with task that has no goal or project
        standalone_task_id = f"task-standalone-{uuid.uuid4().hex[:12]}"
        
        db.execute(text("""
            INSERT INTO tasks 
            (id, title, description, status, priority, created_at, updated_at, verifier_agent_id, goal_id, project_id)
            VALUES (:id, :title, :description, :status, :priority, :created_at, :updated_at, NULL, NULL, NULL)
        """), {
            "id": standalone_task_id,
            "title": "Standalone Task",
            "description": "Task without project or goal",
            "status": "todo",
            "priority": "medium",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        db.commit()
        
        # Test the inheritance mechanism
        from src.reins.scheduler.result_verifier import ResultVerifier
        verifier = ResultVerifier()
        
        # Temporarily override the db manager to use our test database
        original_db = verifier.db
        verifier.db = type('MockDB', (), {
            'engine': engine
        })()
        
        effective_verifier = verifier.resolve_effective_verifier(standalone_task_id)
        
        # Should fall back to default verifier when no hierarchy exists
        assert effective_verifier == "kouzi", f"Expected default verifier 'kouzi', got '{effective_verifier}'"
        print(f"✓ Standalone task (no project/goal) uses default verifier: {effective_verifier}")
        
        # Restore original db
        verifier.db = original_db
        db.close()
        
        print(f"\n✅ EDGE CASE TESTING COMPLETE!")
        print("All edge cases handled correctly")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ EDGE CASE TESTING FAILED: {e}")
        import traceback
        traceback.print_exc()
        db.close()
        raise e


def run_all_tests():
    """
    Run all verifier inheritance validation tests
    """
    print("RUNNING VERIFIER INHERITANCE VALIDATION TESTS")
    print("Goal: goal-cb4c76143b4c")
    print("="*70)
    
    success_count = 0
    total_tests = 2
    
    try:
        # Test 1: Basic inheritance chain
        if test_verifier_inheritance_chain():
            success_count += 1
            print("\n✅ Test 1: Basic inheritance chain - PASSED")
    except Exception as e:
        print(f"\n❌ Test 1: Basic inheritance chain - FAILED: {e}")
    
    try:
        # Test 2: Edge cases
        if test_verifier_inheritance_edge_cases():
            success_count += 1
            print("✅ Test 2: Edge cases - PASSED")
    except Exception as e:
        print(f"❌ Test 2: Edge cases - FAILED: {e}")
    
    print("\n" + "="*70)
    print("FINAL TEST RESULTS")
    print("="*70)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {success_count}")
    print(f"Failed: {total_tests - success_count}")
    
    if success_count == total_tests:
        print("\n🎉 ALL VERIFIER INHERITANCE TESTS PASSED!")
        print("The inheritance mechanism works correctly:")
        print("  ✓ Task without verifier inherits from goal")
        print("  ✓ Task with own verifier uses task-specific")
        print("  ✓ Project with verifier takes precedence over goal")
        print("  ✓ Task without project/goal falls back to default")
        print("  ✓ Inheritance priority: Task > Project > Goal > DEFAULT")
        print("="*70)
        return True
    else:
        print(f"\n❌ {total_tests - success_count} TEST(S) FAILED!")
        print("="*70)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)