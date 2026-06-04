import urllib.request, json

# Check projects for Test Goal
goal_id = 'goal-ddfef4fb53dd'
url = f'http://localhost:8090/api/v1/projects/?goal_id={goal_id}'
print(f'Checking: {url}')
r = urllib.request.urlopen(url)
projs = json.loads(r.read())
print(f'API returned {len(projs)} projects for goal {goal_id}')
for p in projs:
    print(f'  - {p.get("name","?")}')

print()

# Check ALL projects
print('All projects in DB:')
r2 = urllib.request.urlopen('http://localhost:8090/api/v1/projects/')
all_projs = json.loads(r2.read())
for p in all_projs:
    gid = p.get('goal_id', 'null')
    name = p.get('name', '?')
    print(f'  {name:30s} goal_id={gid}')
