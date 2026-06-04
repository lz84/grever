"""Full debug of agent matching API"""
import sys
sys.path.insert(0, 'src')

import json

scenario_id = "scenario-61681331ddca"

from database.config import get_engine
from sqlalchemy import text

engine = get_engine()
with engine.connect() as conn:
    row = conn.execute(text(
        "SELECT agent_requirements FROM scenarios WHERE id = :id"
    ), {"id": scenario_id}).fetchone()

if not row or not row[0]:
    print("ERROR: Scenario not found or no requirements")
    exit(1)

requirements = json.loads(row[0]) if isinstance(row[0], str) else row[0]

# Import and call match
from reins.services.agent_matcher import match_agents_for_scenario

try:
    results = match_agents_for_scenario(requirements)
    print(f"Match results: {len(results)}")
    
    # Build response like the API does
    response = []
    for r in results:
        response.append({
            "role": r.role,
            "required_capabilities": r.required_capabilities,
            "matched_agents": r.matched_agents,
            "missing": r.missing
        })
    
    print(f"Response: {json.dumps(response, ensure_ascii=False)}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
