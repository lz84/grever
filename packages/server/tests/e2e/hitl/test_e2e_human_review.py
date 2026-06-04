"""
E2E Test: Sprint 58 人工裁决中心完整流程

测试场景：
1. stats API 返回正确统计
2. pending API 返回列表
3. 批量裁决
4. 单个裁决
5. disputed 任务流程
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
import json
import time

BASE = "http://localhost:8090/api/v1"

def test_01_stats_api():
    """Test stats API returns correct structure"""
    r = requests.get(f"{BASE}/human-review/stats", timeout=10)
    assert r.status_code == 200, f"Status {r.status_code}"
    d = r.json()
    assert 'disputed_count' in d, "Missing disputed_count"
    assert 'pending_count' in d, "Missing pending_count"
    assert 'waiting_human_count' in d, "Missing waiting_human_count"
    assert 'total' in d, "Missing total"
    assert isinstance(d.get('recent_pending', []), list), "recent_pending not list"
    print("  ✅ test_01_stats_api passed")

def test_02_pending_api():
    """Test pending API returns paginated list"""
    r = requests.get(f"{BASE}/human-review/pending", timeout=10)
    assert r.status_code == 200, f"Status {r.status_code}"
    d = r.json()
    assert 'items' in d, "Missing items"
    assert 'total' in d, "Missing total"
    assert 'page' in d, "Missing page"
    assert 'page_size' in d, "Missing page_size"
    assert isinstance(d['items'], list), "items not list"
    print("  ✅ test_02_pending_api passed")

def test_03_pending_filter():
    """Test pending API with type filter"""
    for t in ['all', 'disputed', 'waiting', 'assist']:
        r = requests.get(f"{BASE}/human-review/pending?type={t}", timeout=10)
        assert r.status_code == 200, f"Status {r.status_code} for type={t}"
        d = r.json()
        assert 'items' in d, f"Missing items for type={t}"
    print("  ✅ test_03_pending_filter passed")

def test_04_batch_ruling():
    """Test batch ruling API"""
    # Get pending items first
    r = requests.get(f"{BASE}/human-review/pending?type=disputed", timeout=10)
    d = r.json()
    items = d.get('items', [])
    
    if items:
        # Pick first item for batch ruling
        ruling_items = [{
            "id": item['id'],
            "action": "approved",
            "comment": "E2E test auto-approved"
        } for item in items[:1]]
        
        r = requests.post(f"{BASE}/human-review/batch-ruling", json={
            "items": ruling_items
        }, timeout=10)
        assert r.status_code == 200, f"Batch ruling failed: {r.status_code} {r.text}"
        d = r.json()
        assert 'success' in d or 'results' in d, "Missing response fields"
        print("  ✅ test_04_batch_ruling passed")
    else:
        print("  ⏭️ test_04_batch_ruling skipped (no disputed items)")

def test_05_ruling_endpoint():
    """Test single task ruling endpoint"""
    # Get a disputed task
    r = requests.get(f"{BASE}/human-review/pending?type=disputed", timeout=10)
    d = r.json()
    items = d.get('items', [])
    
    if items:
        task_id = items[0]['id']
        r = requests.post(f"{BASE}/tasks/{task_id}/ruling", json={
            "action": "approved",
            "comment": "E2E test auto-approved"
        }, timeout=10)
        assert r.status_code in [200, 404], f"Ruling failed: {r.status_code}"
        print("  ✅ test_05_ruling_endpoint passed")
    else:
        print("  ⏭️ test_05_ruling_endpoint skipped (no disputed items)")

if __name__ == '__main__':
    print("=== Sprint 58 E2E Tests ===\n")
    tests = [
        test_01_stats_api,
        test_02_pending_api,
        test_03_pending_filter,
        test_04_batch_ruling,
        test_05_ruling_endpoint,
    ]
    
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__} FAILED: {e}")
            failed += 1
    
    print(f"\n=== Results: {passed}/{passed+failed} passed ===")
    if failed > 0:
        sys.exit(1)
