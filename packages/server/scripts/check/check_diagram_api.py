import urllib.request, json

# Get workflows
r = urllib.request.urlopen('http://localhost:8090/api/v1/workflows')
wfs = json.load(r)
print(f'Workflows from API: {len(wfs)}')

for w in wfs:
    wid = w['id']
    wname = w['name']
    
    # Call diagram API
    url = f'http://localhost:8090/api/v1/workflows/{wid}/diagram'
    try:
        r2 = urllib.request.urlopen(url)
        data = json.load(r2)
        n = len(data.get('nodes', []))
        e = len(data.get('edges', []))
        print(f'  {wname}: {n} nodes, {e} edges')
        if n > 0:
            print(f'    First node: {data["nodes"][0]}')
    except Exception as err:
        print(f'  {wname}: ERROR - {err}')
