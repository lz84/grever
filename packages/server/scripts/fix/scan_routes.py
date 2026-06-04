import re, os

routes = []
for root, dirs, files in os.walk('src'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                content = fh.read()
                for m in re.finditer(r'@(?:router|app)\.(get|post|put|delete|patch)\([\"\']([^\"\']+)[\"\']', content):
                    routes.append((m.group(1).upper(), m.group(2), path))
                for m in re.finditer(r'include_router\([^)]*prefix=[\"\']([^\"\']+)[\"\']', content):
                    routes.append(('PREFIX', m.group(1), path))

for method, path, src in sorted(routes, key=lambda x: x[1]):
    print(f'{method:8s} {path:50s} ({src})')
