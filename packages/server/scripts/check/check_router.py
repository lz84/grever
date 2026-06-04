import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from reins.api.project_workflow import router

print(f'Router prefix: {router.prefix}')
print(f'Router routes: {len(router.routes)}')
for route in router.routes:
    print(f'  - {route.path}: {route.methods}')
