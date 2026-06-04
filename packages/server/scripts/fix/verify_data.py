import urllib.request, json

r = urllib.request.urlopen('http://localhost:8090/api/v1/goals')
goals = json.load(r)
print(f'Goals: {len(goals)}')
for g in goals:
    print(f'  {g["id"]} - {g["title"]} ({g["status"]})')

r = urllib.request.urlopen('http://localhost:8090/api/v1/projects')
projs = json.load(r)
print(f'\nProjects: {len(projs)}')
for p in projs:
    print(f'  {p["id"]} - {p["name"]} ({p["status"]}) goal={p["goal_id"]}')

r = urllib.request.urlopen('http://localhost:8090/api/v1/tasks')
tasks = json.load(r)
print(f'\nTasks: {len(tasks)}')
for t in tasks:
    print(f'  {t["id"]} - {t["title"]} ({t["status"]}) proj={t["project_id"]}')
