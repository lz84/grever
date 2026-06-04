import urllib.request, json

for gid in ['goal-ddfef4fb53dd', 'goal-001', None]:
    if gid:
        url = f'http://localhost:8090/api/v1/projects?goal_id={gid}'
    else:
        url = 'http://localhost:8090/api/v1/projects'
    r = urllib.request.urlopen(url)
    data = json.loads(r.read())
    label = f'goal_id={gid}' if gid else 'All'
    print(f'{label}: {len(data)} projects')
    for p in data:
        print(f'    {p["id"]:20s} {p["name"]:20s} goal_id={p.get("goal_id")}')
