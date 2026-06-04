import urllib.request, json
r = urllib.request.urlopen('http://localhost:8090/api/v1/projects')
projects = json.load(r)
print(f'Projects: {len(projects)}')
for p in projects:
    goal_id = p.get('goal_id', '?')
    print(f'  {p["name"]} -> goal_id: {goal_id}')
