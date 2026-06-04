"""
使用 FastAPI TestClient 直接测试 goals API
"""
import sys
import os

# os.chdir removed - using dynamic path resolution
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from api.server import create_app

app = create_app()
client = TestClient(app)

print("Testing GET /api/v1/goals")
response = client.get("/api/v1/goals")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

print("\nTesting GET /api/v1/agents")
response = client.get("/api/v1/agents")
print(f"Status: {response.status_code}")
data = response.json()
print(f"Agents count: {len(data)}")
for a in data:
    print(f"  - {a.get('name')} ({a.get('id')})")
