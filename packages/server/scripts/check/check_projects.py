import urllib.request, json

# Check all projects
r = urllib.request.urlopen('http://localhost:8090/api/v1/projects/')
projects = json.loads(r.read())
print(f'Total projects: {len(projects)}')
for p in projects:
    name = p.get('name', '')
    gid = p.get('goal_id')
    print(f'  {name:30s} goal_id={gid}')

print()

# Filter by first goal
goal_id = 'e1092ac865ce49e8a04c5bb672ac276b'
r2 = urllib.request.urlopen(f'http://localhost:8090/api/v1/projects/?goal_id={goal_id}')
filtered = json.loads(r2.read())
print(f'Projects for goal {goal_id[:12]}...: {len(filtered)}')
for p in filtered:
    name = p.get('name', '')
    gid = p.get('goal_id')
    print(f'  {name:30s} goal_id={gid}')

print()

# Filter by second goal
goal_id2 = '07479f1714fe4e5a8acc66c17eabcf69'
r3 = urllib.request.urlopen(f'http://localhost:8090/api/v1/projects/?goal_id={goal_id2}')
filtered2 = json.loads(r3.read())
print(f'Projects for goal {goal_id2[:12]}...: {len(filtered2)}')
for p in filtered2:
    name = p.get('name', '')
    gid = p.get('goal_id')
    print(f'  {name:30s} goal_id={gid}')
