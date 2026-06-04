import urllib.request, json

# Get all goals
r = urllib.request.urlopen('http://localhost:8090/api/v1/goals/')
goals = json.loads(r.read())
print(f'Total goals: {len(goals)}')
for g in goals:
    gid = g.get('id', '')
    title = g.get('title', '')
    print(f'  Goal: {title:30s} id={gid[:20]}...')

print()

# For each goal, check projects
for g in goals:
    gid = g.get('id', '')
    title = g.get('title', '')
    r2 = urllib.request.urlopen(f'http://localhost:8090/api/v1/projects/?goal_id={gid}')
    projects = json.loads(r2.read())
    print(f'Goal "{title}" ({gid[:12]}...): {len(projects)} projects')
    for p in projects:
        print(f'  - {p.get("name")}')
    print()
