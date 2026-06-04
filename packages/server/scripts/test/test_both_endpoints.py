import urllib.request, json

# Test regular endpoint with filter
url = 'http://localhost:8090/api/v1/projects?goal_id=goal-ddfef4fb53dd'
r = urllib.request.urlopen(url)
data = json.loads(r.read())
print(f'Regular endpoint: {len(data)} projects')
for p in data:
    print(f'  {p["id"]:20s} goal_id={p.get("goal_id")}')

# Test debug endpoint
url2 = 'http://localhost:8090/api/v1/projects/debug-filter?goal_id=goal-ddfef4fb53dd'
r2 = urllib.request.urlopen(url2)
data2 = json.loads(r2.read())
print(f'Debug endpoint: {data2["filtered_count"]} projects')
print(f'Debug goal_id_param: {data2["goal_id_param"]}')
