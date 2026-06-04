import urllib.request, json
r = urllib.request.urlopen('http://localhost:8090/api/v1/goals/goal-chemical-leak-001/tree')
tree = json.load(r)
print('Goal:', tree.get('title') or tree.get('name'))
print('Status:', tree.get('status'))
print('Projects:', len(tree.get('children', [])))
for child in tree.get('children', []):
    tasks = child.get('children', [])
    print(f'  - {child.get("name") or child.get("title")} [{child.get("status")}] ({len(tasks)} tasks)')
    for t in tasks[:3]:
        print(f'      [{t.get("status")}] {t.get("title") or t.get("name")} @{t.get("assigned_agent","")}')
    if len(tasks) > 3:
        print(f'      ... and', len(tasks)-3, 'more')
