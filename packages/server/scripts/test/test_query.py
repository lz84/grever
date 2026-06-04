import sqlite3
from sqlalchemy import create_engine, text

# 使用 SQLAlchemy 连接数据库
engine = create_engine('sqlite:///D:/work/research/agents-nexus/data/reins.db')

with engine.connect() as conn:
    proj_id = 'proj-2882a8ff'
    result = conn.execute(text('SELECT id, name, description, status FROM projects WHERE id = :id'), {'id': proj_id}).fetchone()
    print(f'Project found: {result}')
