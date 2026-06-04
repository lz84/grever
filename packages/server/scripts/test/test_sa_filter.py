import sys
sys.path.insert(0, r'D:\work\research\agents-nexus\packages\server\src')

from database.config import DB_CONFIG
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from reins.models.project import Project

print(f"DB URL: {DB_CONFIG.url}")

engine = create_engine(DB_CONFIG.url)
with Session(engine) as session:
    # Test 1: All projects
    all_projs = session.query(Project).all()
    print(f"\nAll projects: {len(all_projs)}")
    for p in all_projs:
        print(f"  {p.id:20s} {p.name:20s} goal_id={p.goal_id!r}")
    
    # Test 2: Filter by goal_id
    filtered = session.query(Project).filter(Project.goal_id == 'goal-ddfef4fb53dd').all()
    print(f"\nFilter goal_id='goal-ddfef4fb53dd': {len(filtered)}")
    
    # Test 3: Filter by goal-001
    filtered2 = session.query(Project).filter(Project.goal_id == 'goal-001').all()
    print(f"Filter goal_id='goal-001': {len(filtered2)}")
    
    # Test 4: Raw SQL
    from sqlalchemy import text
    result = session.execute(text("SELECT COUNT(*) FROM projects WHERE goal_id = :gid"), {"gid": "goal-ddfef4fb53dd"})
    count = result.scalar()
    print(f"Raw SQL filter: {count}")
