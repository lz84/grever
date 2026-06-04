import re, os

SRC = r"D:\work\research\agents-nexus\packages\server\src\reins\api\solutions.py"
DIR = os.path.dirname(SRC)
L = open(SRC, encoding='utf-8').readlines()

# Find all endpoints
endpoints = []
for i, line in enumerate(L):
    s = line.strip()
    if s.startswith('@router.'):
        m = re.search(r'["\'](/[^"\']+)["\']', s)
        path = m.group(1) if m else '?'
        next_r = None
        for j in range(i+1, len(L)):
            if L[j].strip().startswith('@router.'):
                next_r = j
                break
        el = next_r if next_r else len(L)
        print(f"{i+1}-{el}: {path} ({el-i} lines)")
        endpoints.append((i+1, el, path))

# Key boundary: where does iteration (/goals/) start?
iter_start = None
for start, end, path in endpoints:
    if '/goals' in path and 'iteration' in path.lower():
        iter_start = start
        break
print(f"\nIteration starts at line: {iter_start}")
print(f"Main endpoints end at: {endpoints[-2][1] if len(endpoints) > 1 else '?'}")
