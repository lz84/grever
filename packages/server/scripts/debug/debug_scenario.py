"""调试 scenario.agent_requirements"""
import sys
sys.path.insert(0, 'src')

from database.config import get_engine
from sqlalchemy import text

engine = get_engine()
with engine.connect() as conn:
    # 获取刚创建的 scenario
    scenario_id = "scenario-84358003a8f6"
    row = conn.execute(text("SELECT agent_requirements, typeof(agent_requirements) FROM scenarios WHERE id = :id"), {"id": scenario_id}).fetchone()
    print(f"Row: {row}")
    if row:
        print(f"  agent_requirements: {row[0]}")
        print(f"  type: {row[1]}")
        print(f"  is None: {row[0] is None}")
        print(f"  bool(agent_requirements): {bool(row[0])}")
