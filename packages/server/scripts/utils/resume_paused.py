import urllib.request, json

r = urllib.request.urlopen('http://192.168.1.9:8096/api/v1/tasks?goal_id=goal-8b167a357e40')
tasks = json.loads(r.read()).get('tasks', [])
paused = [t for t in tasks if t.get('status') == 'paused']
print(f"Paused tasks: {len(paused)}")
for t in paused:
    tid = t.get('id', '?')
    title = (t.get('title', '') or '')[:40]
    print(f"  {tid} | {title}")
    try:
        req = urllib.request.Request(
            f'http://192.168.1.9:8096/api/v1/tasks/{tid}/resume',
            data=b'', method='POST',
            headers={'Content-Type': 'application/json'}
        )
        resp = urllib.request.urlopen(req)
        print(f"    → resumed OK")
    except Exception as e:
        print(f"    → ERROR: {e}")
