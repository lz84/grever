import urllib.request, json

r = urllib.request.urlopen('http://localhost:8090/api/v1/goals/')
goals = json.loads(r.read())

for g in goals:
    gid = g.get('id', '')
    title = g.get('title', '')
    r2 = urllib.request.urlopen(f'http://localhost:8090/api/v1/projects/?goal_id={gid}')
    projs = json.loads(r2.read())
    print(f"Goal: {title}")
    print(f"  ID: {gid}")
    print(f"  Projects: {len(projs)}")
    for p in projs:
        print(f"    - {p.get('name')} (goal_id={p.get('goal_id')})")
    print()
