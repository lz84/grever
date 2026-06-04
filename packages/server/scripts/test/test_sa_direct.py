import sys
sys.path.insert(0, r'D:\work\research\agents-nexus\packages\server\src')

from database.config import DB_CONFIG
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy import Column, String, Integer, DateTime, Text
from datetime import datetime

print(f"DB URL: {DB_CONFIG.url}")

engine = create_engine(DB_CONFIG.url)

# Define a minimal model that matches the actual schema
Base = declarative_base()

class SimpleProject(Base):
    __tablename__ = 'projects'
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    goal_id = Column(String(36), nullable=True)
    status = Column(String(20), nullable=False)
    priority = Column(String(20), nullable=True)
    assignee = Column(String(255), nullable=True)
    due_date = Column(String(50), nullable=True)
    workflow_id = Column(String(36), nullable=True)
    phase_order = Column(Integer, nullable=True)
    matched_scenario_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    members = Column(Text, nullable=True)
    task_ids = Column(Text, nullable=True)

with Session(engine) as session:
    # Test 1: All
    all_projs = session.query(SimpleProject).all()
    print(f"\nAll projects: {len(all_projs)}")
    for p in all_projs:
        print(f"  {p.id:20s} {p.name:20s} goal_id={p.goal_id!r}")
    
    # Test 2: Filter
    q1 = session.query(SimpleProject).filter(SimpleProject.goal_id == 'goal-ddfef4fb53dd')
    print(f"\nSQL: {q1}")
    filtered1 = q1.all()
    print(f"Filter goal_id='goal-ddfef4fb53dd': {len(filtered1)}")
    
    # Test 3: Filter
    q2 = session.query(SimpleProject).filter(SimpleProject.goal_id == 'goal-001')
    print(f"\nSQL: {q2}")
    filtered2 = q2.all()
    print(f"Filter goal_id='goal-001': {len(filtered2)}")
    
    # Test 4: Raw SQL
    from sqlalchemy import text
    result = session.execute(
        text("SELECT COUNT(*) FROM projects WHERE goal_id = :gid"),
        {"gid": "goal-ddfef4fb53dd"}
    )
    count = result.scalar()
    print(f"\nRaw SQL filter: {count}")
