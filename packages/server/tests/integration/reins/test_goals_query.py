import sys
import os

# os.chdir removed - using dynamic path resolution
sys.path.insert(0, '.')

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from reins.common.database import get_db_session, get_db_manager
from models.goal import Goal

# Test the exact same query the router uses
session = get_db_session()
try:
    query = session.query(Goal)
    goals = query.all()
    print(f"query(Goal).all() returned {len(goals)} goals")
    for g in goals:
        print(f"  - {g.title} ({g.id})")
        d = g.to_dict()
        print(f"    to_dict: {d}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

session.close()
