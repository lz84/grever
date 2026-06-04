"""Test Grasp plans API endpoint"""
import sys, json
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from api.server import create_app

app = create_app()
client = TestClient(app)

# Test 1: Search with keyword
resp = client.get('/api/v1/grasp/plans?q=地震')
data = resp.json()
print(f"Test 1 - Search 地震: status={resp.status_code}, results={data['total']}")
for r in data.get('results', []):
    title = r['plan']['title']
    score = r['score']
    matched = r['matched_keywords']
    print(f"  - {title}: score={score}, matched={matched}")
assert resp.status_code == 200
assert data['total'] >= 1

# Test 2: Search empty (return all)
resp = client.get('/api/v1/grasp/plans')
data = resp.json()
print(f"Test 2 - All plans: status={resp.status_code}, results={data['total']}")
assert resp.status_code == 200
assert data['total'] >= 3

# Test 3: Search with multiple keywords
resp = client.get('/api/v1/grasp/plans?q=城市 搜救')
data = resp.json()
print(f"Test 3 - Search 城市 搜救: status={resp.status_code}, results={data['total']}")
for r in data.get('results', []):
    title = r['plan']['title']
    score = r['score']
    matched = r['matched_keywords']
    print(f"  - {title}: score={score}, matched={matched}")
assert resp.status_code == 200

# Test 4: Get single plan
resp = client.get('/api/v1/grasp/plans/plan-earthquake-001')
data = resp.json()
print(f"Test 4 - Get plan: status={resp.status_code}")
assert resp.status_code == 200
assert 'plan' in data

# Test 5: Get non-existent plan
resp = client.get('/api/v1/grasp/plans/nonexistent')
print(f"Test 5 - Get nonexistent: status={resp.status_code}")
assert resp.status_code == 404

print()
print("All endpoint tests passed!")
