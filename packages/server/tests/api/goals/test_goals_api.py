import sys
import os

# os.chdir removed - using dynamic path resolution
sys.path.insert(0, '.')

from sqlalchemy import text
from reins.common.database import get_db_session

session = get_db_session()
result = session.execute(text('SELECT COUNT(*) FROM goals'))
count = result.scalar()
print(f"Goals count via get_db_session: {count}")

if count > 0:
    result = session.execute(text('SELECT id, title FROM goals'))
    for row in result:
        print(f"  - {row[1]} ({row[0]})")

session.close()
