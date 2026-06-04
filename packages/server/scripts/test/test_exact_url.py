import urllib.request, json

# Test the EXACT same URL the frontend uses
url = 'http://localhost:8090/api/v1/projects?goal_id=goal-ddfef4fb53dd'
print(f'Testing: {url}')
r = urllib.request.urlopen(url)
data = json.loads(r.read())
print(f'Count: {len(data)}')
for p in data:
    print(f'  - {p.get("name","?")} (goal_id={p.get("goal_id")})')
