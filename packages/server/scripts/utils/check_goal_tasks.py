import urllib.request, json
from collections import Counter

r = urllib.request.urlopen('http://192.168.1.9:8096/api/v1/tasks?goal_id=goal-8b167a357e40')
tasks = json.loads(r.read()).get('tasks', [])
counts = Counter(t.get('status') for t in tasks)
print('Task counts:', dict(counts))
for t in tasks:
    s = t.get('status')
    if s in ['in_progress', 'done', 'failed', 'timeout']:
        print(f'  {t["id"]} | {s} | {t.get("title","")[:40]}')
