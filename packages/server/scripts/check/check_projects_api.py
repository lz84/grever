import urllib.request, json
r = urllib.request.urlopen('http://localhost:8090/api/v1/projects')
projects = json.load(r)
print(f'Projects: {len(projects)}')
for p in projects:
    print(f'  {p["id"]} -> goal_id={p.get("goal_id","null")}')
