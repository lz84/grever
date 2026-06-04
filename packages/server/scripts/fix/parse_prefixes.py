import re, os

with open('src/reins/api/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

for m in re.finditer(r'include_router\((\w+)', content):
    module = m.group(1)
    start = m.end()
    chunk = content[start:start+300]
    prefix_m = re.search(r'prefix=["\']([^"\']+)["\']', chunk)
    prefix = prefix_m.group(1) if prefix_m else '(no prefix)'
    print(f'{module}: {prefix}')
