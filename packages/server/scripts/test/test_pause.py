import sqlite3
import requests
import json

# 连接数据库
conn = sqlite3.connect(r'D:\work\research\agents-nexus\data\reins.db')
cursor = conn.cursor()

# 检查项目是否存在
cursor.execute('SELECT id, name, status FROM projects WHERE id = ?', ('proj-2882a8ff',))
proj = cursor.fetchone()
print(f'Project: {proj}')

# 检查任务状态
cursor.execute('SELECT id, title, project_id, status FROM tasks WHERE project_id = ?', ('proj-2882a8ff',))
tasks = cursor.fetchall()
print(f'Tasks before pause: {tasks}')

conn.close()

# 发送暂停请求
url = 'http://localhost:8091/api/v1/projects/proj-2882a8ff/status?status=on_hold'
print(f'\nSending PATCH request to: {url}')
response = requests.patch(url)
print(f'Response code: {response.status_code}')
print(f'Response body: {response.text}')

# 重新连接数据库检查结果
conn = sqlite3.connect(r'D:\work\research\agents-nexus\data\reins.db')
cursor = conn.cursor()

# 检查项目状态
cursor.execute('SELECT id, name, status FROM projects WHERE id = ?', ('proj-2882a8ff',))
proj = cursor.fetchone()
print(f'\nProject after pause: {proj}')

# 检查任务状态
cursor.execute('SELECT id, title, project_id, status FROM tasks WHERE project_id = ?', ('proj-2882a8ff',))
tasks = cursor.fetchall()
print(f'Tasks after pause: {tasks}')

conn.close()
