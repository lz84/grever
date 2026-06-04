import sys
import os
os.chdir(os.path.dirname(__file__))
from models.task import TaskCreate, Task
tc = TaskCreate(
    title='test',
    description='test desc',
    priority='high',
    status='todo',
    project_id='proj-8dca493663e1',
    capability_tags={"technical": ["python"]},
    depends_on=[],
    acceptance_criteria='{"criteria":[{"type":"compile","desc":"compile pass"}]}'
)
d = tc.model_dump(exclude_none=True)
print('Keys:', list(d.keys()))
print('acceptance_criteria:', repr(d.get('acceptance_criteria')))
t = Task(**d)
print('Task created OK')
