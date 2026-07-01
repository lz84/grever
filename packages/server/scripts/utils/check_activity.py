import urllib.request, json

r = urllib.request.urlopen('http://192.168.1.9:8096/api/v1/agents')
data = json.loads(r.read())
for a in data:
    print(a.get('id', '?'), '| name=', a.get('name', '?'), '| status=', a.get('status', '?'))
