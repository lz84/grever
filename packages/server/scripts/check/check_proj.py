import urllib.request, json

# Check all projects
r = urllib.request.urlopen('http://localhost:8090/api/v1/projects/')
projects = json.loads(r.read())
print(f"Total projects: {len(projects)}")
for p in projects:
    name = p.get("name", "?")
    gid = str(p.get("goal_id", "null"))[:20]
    print(f"  {name:30s}  goal_id={gid}")
