"""Debug SQLAlchemy result type"""
import sys
sys.path.insert(0, 'src')

import json
from database.config import get_engine
from sqlalchemy import text

engine = get_engine()
with engine.connect() as conn:
    row = conn.execute(text(
        "SELECT agent_requirements FROM scenarios WHERE id = :id"
    ), {"id": "scenario-61681331ddca"}).fetchone()
    
    print(f"Row type: {type(row)}")
    print(f"Row: {row}")
    print(f"row[0]: {row[0]}")
    print(f"type(row[0]): {type(row[0])}")
    print(f"hasattr(row, 'agent_requirements'): {hasattr(row, 'agent_requirements')}")
    
    # Try accessing as attribute
    try:
        print(f"row.agent_requirements: {row.agent_requirements}")
        print(f"type(row.agent_requirements): {type(row.agent_requirements)}")
    except Exception as e:
        print(f"Error accessing row.agent_requirements: {e}")
