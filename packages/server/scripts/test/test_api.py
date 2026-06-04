"""测试 Agent 匹配 API"""
import sys
sys.path.insert(0, 'src')

import requests
import time

BASE_URL = "http://localhost:8090"

def test_match_agents():
    """测试 /api/v1/agent-matching/match"""
    try:
        # 先获取一个 scenarios 列表
        r = requests.get(f"{BASE_URL}/api/v1/scenarios", timeout=5)
        if r.status_code != 200:
            print(f"SKIP: scenarios API not available ({r.status_code})")
            return
        scenarios = r.json()
        if not scenarios:
            print("SKIP: no scenarios found")
            return
        
        scenario_id = scenarios[0]['id']
        payload = {"scenario_id": scenario_id}
        r = requests.post(f"{BASE_URL}/api/v1/agent-matching/match", json=payload, timeout=5)
        print(f"POST /api/v1/agent-matching/match: {r.status_code}")
        if r.status_code == 200:
            print(f"  Response: {r.json()}")
        else:
            print(f"  Error: {r.text}")
    except requests.exceptions.RequestException as e:
        print(f"SKIP: HTTP request failed - {e}")

def test_trust_level_update():
    """测试 /api/v1/agent-matching/trust-levels/update"""
    try:
        r = requests.post(f"{BASE_URL}/api/v1/agent-matching/trust-levels/update", timeout=5)
        print(f"POST /api/v1/agent-matching/trust-levels/update: {r.status_code}")
        if r.status_code == 200:
            print(f"  Response: {r.json()}")
        else:
            print(f"  Error: {r.text}")
    except requests.exceptions.RequestException as e:
        print(f"SKIP: HTTP request failed - {e}")

def test_get_trust_level():
    """测试 /api/v1/agent-matching/trust-levels/{scenario_id}"""
    try:
        # 先获取一个 scenarios 列表
        r = requests.get(f"{BASE_URL}/api/v1/scenarios", timeout=5)
        if r.status_code != 200:
            print(f"SKIP: scenarios API not available ({r.status_code})")
            return
        scenarios = r.json()
        if not scenarios:
            print("SKIP: no scenarios found")
            return
        
        scenario_id = scenarios[0]['id']
        r = requests.get(f"{BASE_URL}/api/v1/agent-matching/trust-levels/{scenario_id}", timeout=5)
        print(f"GET /api/v1/agent-matching/trust-levels/{scenario_id}: {r.status_code}")
        if r.status_code == 200:
            print(f"  Response: {r.json()}")
        else:
            print(f"  Error: {r.text}")
    except requests.exceptions.RequestException as e:
        print(f"SKIP: HTTP request failed - {e}")

if __name__ == "__main__":
    print("Testing Agent Matching API...")
    print("=" * 50)
    test_match_agents()
    print()
    test_trust_level_update()
    print()
    test_get_trust_level()
    print("=" * 50)
    print("Done!")
