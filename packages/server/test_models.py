import sys
sys.path.insert(0, 'src')
import os
os.environ['SQLITE_PATH'] = 'D:/work/research/agents-nexus/data/reins.db'
from reins.models import Task, Goal, Project, Agent
print('Models imported OK')
