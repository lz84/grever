import sqlite3
import uuid
from datetime import datetime

conn = sqlite3.connect(r'D:\work\research\agents-nexus\data\reins.db')
cursor = conn.cursor()

# 创建测试项目
test_proj_id = f"proj-test-{str(uuid.uuid4())[:8]}"
cursor.execute('''
    INSERT INTO projects (id, name, description, goal_id, status, members, task_ids, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (test_proj_id, 'Sprint 36 Test Project', 'Test project for Sprint 36', None, 'active', '[]', '[]', datetime.now().isoformat(), datetime.now().isoformat()))

# 创建测试任务
test_task_id = f"task-test-{str(uuid.uuid4())[:8]}"
cursor.execute('''
    INSERT INTO tasks (id, title, description, project_id, goal_id, assigned_agent, status, priority, category, dependencies, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (test_task_id, 'Test Task In Progress', 'This task should be affected by project pause', test_proj_id, None, 'agent-command', 'in_progress', 1, 'test', '[]', datetime.now().isoformat(), datetime.now().isoformat()))

conn.commit()
conn.close()

print(f'Created test project: {test_proj_id}')
print(f'Created test task: {test_task_id}')
