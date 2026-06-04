"""Debug agent matching API directly"""
import sys
sys.path.insert(0, 'src')

import json

# Simulate what the API does
scenario_id = "scenario-61681331ddca"

from database.config import get_engine
from sqlalchemy import text

engine = get_engine()
with engine.connect() as conn:
    row = conn.execute(text(
        "SELECT agent_requirements FROM scenarios WHERE id = :id"
    ), {"id": scenario_id}).fetchone()

print(f"Row: {row}")
print(f"agent_requirements: {row[0]}")

if row and row[0]:
    # Parse
    requirements = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    print(f"Parsed requirements: {requirements}")
    
    # Try match
    from reins.services.agent_matcher import match_agents_for_scenario
    try:
        results = match_agents_for_scenario(requirements)
        print(f"Results: {results}")
        for r in results:
            print(f"  Role: {r.role}")
            print(f"  Required caps: {r.required_capabilities}")
            print(f"  Matched agents: {r.matched_agents}")
            print(f"  Missing: {r.missing}")
    except Exception as e:
        print(f"ERROR during match: {e}")
        import traceback
        traceback.print_exc()
