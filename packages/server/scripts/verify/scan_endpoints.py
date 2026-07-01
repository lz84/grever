#!/usr/bin/env python
"""Scan all router files and produce a clean list of all API endpoints."""
import re
from pathlib import Path
import importlib.util
import sys

SRC = Path("src")

# Step 1: Find all router variable definitions and their prefixes
router_info = {}  # router_var_name -> (file_path, file_prefix)

# Scan all Python files for APIRouter(prefix=...) assignments
for pyfile in SRC.rglob("*.py"):
    try:
        content = pyfile.read_text(encoding="utf-8")
    except:
        continue
    
    # Find router = APIRouter(prefix="...") 
    for m in re.finditer(r'(\w+)\s*=\s*APIRouter\([^)]*prefix\s*=\s*["\']([^"\']*)["\']', content):
        var_name = m.group(1)
        prefix = m.group(2)
        rel = pyfile.relative_to(SRC)
        router_info[var_name] = (str(rel), prefix)

# Step 2: For each router, extract @router.get/post/... decorators
endpoints = []
for router_var, (filepath, prefix) in router_info.items():
    full = SRC / filepath
    try:
        content = full.read_text(encoding="utf-8")
    except:
        continue
    
    for m in re.finditer(r'@router\.(get|post|put|patch|delete)\(\s*["\']([^"\']*)["\']', content):
        method = m.group(1).upper()
        path_suffix = m.group(2)
        full_path = prefix + path_suffix if path_suffix != "/" else prefix
        full_path = re.sub(r'(?<!:)//+', '/', full_path)  # clean double slashes
        endpoints.append((method, full_path, filepath))

# Also check server.py for @app.routes
server_path = SRC / "api" / "server.py"
if server_path.exists():
    try:
        content = server_path.read_text(encoding="utf-8")
        for m in re.finditer(r'@app\.(get|post|put|patch|delete)\(\s*["\']([^"\']*)["\']', content):
            method = m.group(1).upper()
            path = m.group(2)
            endpoints.append((method, path, "api/server.py"))
    except:
        pass

# Deduplicate
seen = set()
unique = []
for method, path, src in sorted(endpoints, key=lambda x: x[1]):
    key = f"{method} {path}"
    if key not in seen:
        seen.add(key)
        unique.append((method, path, src))

print(f"TOTAL UNIQUE ENDPOINTS: {len(unique)}")
print()
for method, path, src in unique:
    print(f"{method:7s} {path}  [{src}]")
