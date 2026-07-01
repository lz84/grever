"""Check for remaining old mode references in Python source files"""
import os, re

src_dir = r'D:\work\research\agents-nexus\packages\server\src'
exclude_dirs = {'__pycache__', 'node_modules', '.git', '.pytest_cache'}
exclude_files = {'021_goal_mode_consolidation.py'}

pattern = re.compile(r'["\']normal["\']|["\']exploration["\']|["\']optimization["\']')

for root, dirs, files in os.walk(src_dir):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for fname in files:
        if not fname.endswith('.py') or fname in exclude_files:
            continue
        fpath = os.path.join(root, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                for lineno, line in enumerate(f, 1):
                    m = pattern.search(line)
                    if m:
                        rel = os.path.relpath(fpath, src_dir)
                        print(f"{rel}:{lineno}: {line.rstrip()}")
        except Exception as e:
            print(f"ERROR reading {fpath}: {e}")

print("\nDone.")
