import urllib.request, json

r = urllib.request.urlopen('http://localhost:8090/api/v1/goals')
goals = json.load(r)
print(f'Goals: {len(goals)}')
for g in goals:
    print(f'  - {g["title"]} [{g["status"]}]')

r = urllib.request.urlopen('http://localhost:8090/api/v1/workflows')
wfs = json.load(r)
print(f'\nWorkflows: {len(wfs)}')
for w in wfs:
    print(f'  - {w["name"]} [{w["status"]}] goal={w["goal_id"]}')

# 验证流程图 API
for w in wfs[:1]:
    url = f'http://localhost:8090/api/v1/workflows/{w["id"]}/diagram'
    r = urllib.request.urlopen(url)
    data = json.load(r)
    print(f'\nDiagram for {w["name"]}:')
    nodes = data.get('dag', {}).get('nodes', []) if isinstance(data.get('dag'), dict) else []
    edges = data.get('dag', {}).get('edges', []) if isinstance(data.get('dag'), dict) else []
    print(f'  Nodes: {len(nodes)}')
    for n in nodes:
        print(f'    {n.get("id","?")}: {n.get("name","?")}')
    print(f'  Edges: {len(edges)}')
