"""测试 Agent matcher 导入"""
import sys
sys.path.insert(0, 'src')

try:
    from reins.services.agent_matcher import match_agents_for_scenario, calculate_trust_level, update_all_trust_levels
    print("PASS: agent_matcher.py import")
    print(f"  - match_agents_for_scenario: {match_agents_for_scenario}")
    print(f"  - calculate_trust_level: {calculate_trust_level}")
    print(f"  - update_all_trust_levels: {update_all_trust_levels}")
except Exception as e:
    print(f"FAIL: agent_matcher.py import - {e}")
    import traceback
    traceback.print_exc()

try:
    from reins.api.agent_matching import router
    print("PASS: agent_matching.py import")
    print(f"  - router: {router}")
except Exception as e:
    print(f"FAIL: agent_matching.py import - {e}")
    import traceback
    traceback.print_exc()
