import urllib.request, json

r = urllib.request.urlopen('http://localhost:8090/api/v1/goals/')
goals = json.loads(r.read())

for g in goals:
    gid = g.get('id', '')
    title = g.get('title', '')
    r2 = urllib.request.urlopen(f'http://localhost:8090/api/v1/projects/?goal_id={gid}')
    projs = json.loads(r2.read())
    print(f'Goal: {title[:30]:30s} -> {len(projs)} projects')
    for p in projs:
        print(f'    - {p.get("name", "?")}')
    print()
