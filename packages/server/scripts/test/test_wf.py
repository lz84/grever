import urllib.request, json
r = urllib.request.urlopen('http://localhost:8090/api/v1/projects/')
projects = json.loads(r.read())
wfs = [p for p in projects if p.get('workflow_id')]
print(f'Found {len(wfs)} projects with workflows')
for p in wfs[:5]:
    print(f'Project: {p["name"]} -> Workflow: {p["workflow_id"]}')
