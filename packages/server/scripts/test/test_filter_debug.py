import urllib.request, json

# Get all projects with their goal_ids
r = urllib.request.urlopen('http://localhost:8090/api/v1/projects/')
projects = json.loads(r.read())

print('All projects and their goal_ids:')
for p in projects:
    name = p.get('name', '?')
    goal_id = p.get('goal_id')
    print(f'  {name:30s} goal_id={goal_id}')

print()

# Now test filtering with each unique goal_id
unique_gids = set(p.get('goal_id') for p in projects if p.get('goal_id'))
for gid in unique_gids:
    url = f'http://localhost:8090/api/v1/projects?goal_id={gid}'
    r2 = urllib.request.urlopen(url)
    filtered = json.loads(r2.read())
    print(f'Filter by goal_id={gid[:20]}... -> {len(filtered)} projects')

# Test with the Test Goal ID
test_gid = 'goal-ddfef4fb53dd'
url = f'http://localhost:8090/api/v1/projects?goal_id={test_gid}'
r3 = urllib.request.urlopen(url)
test_filtered = json.loads(r3.read())
print(f'\nFilter by goal_id={test_gid} -> {len(test_filtered)} projects')
