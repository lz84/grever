"""测试 Agent 匹配 API - 创建测试数据"""
import sys
sys.path.insert(0, 'src')

import requests
import json

BASE_URL = "http://localhost:8090"

def create_test_scenario():
    """创建带 agent_requirements 的测试场景"""
    payload = {
        "name": "Test Agent Matching",
        "category": "fire",
        "status": "active",
        "version": "v1.0",
        "description": "Test scenario for agent matching",
        "scenario_desc": "Test scenario for agent matching",
        "triggers": ["fire_detected"],
        "agent_requirements": [
            {"role": "Monitor", "capabilities": ["monitoring"], "min_agents": 1, "max_agents": 1},
            {"role": "Scheduler", "capabilities": ["logistics"], "min_agents": 1, "max_agents": 2}
        ]
    }
    
    try:
        r = requests.post(f"{BASE_URL}/api/v1/scenarios", json=payload, timeout=5)
        print(f"POST /api/v1/scenarios: {r.status_code}")
        if r.status_code == 200 or r.status_code == 201:
            data = r.json()
            print(f"  Scenario ID: {data['id']}")
            return data['id']
        else:
            print(f"  Error: {r.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Create scenario - {e}")
        return None

def test_match_agents(scenario_id):
    """测试 /api/v1/agent-matching/match"""
    payload = {"scenario_id": scenario_id}
    try:
        r = requests.post(f"{BASE_URL}/api/v1/agent-matching/match", json=payload, timeout=5)
        print(f"POST /api/v1/agent-matching/match (scenario_id={scenario_id}): {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  Response: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"  Error: {r.text}")
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Match agents - {e}")

if __name__ == "__main__":
    print("Testing Agent Matching API with test data...")
    print("=" * 60)
    
    # 创建测试场景
    scenario_id = create_test_scenario()
    if scenario_id:
        print()
        # 等待一小会儿让数据库提交
        import time
        time.sleep(0.5)
        
        # 测试匹配
        test_match_agents(scenario_id)
    
    print("=" * 60)
    print("Done!")
