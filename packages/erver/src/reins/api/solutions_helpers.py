"""Create solutions_helpers.py with compare_solutions and adjust_constraints"""
import os

SRC = r"D:\work\research\agents-nexus\packages\server\src\reins\api\solutions.py"
DIR = os.path.dirname(SRC)
L = open(SRC, encoding='utf-8').readlines()

out = []
out.append('# -*- coding: utf-8 -*-\n')
out.append('"""Compare engine, scoring, constraint adjustment."""\n\n')
out.append('import json, logging\n')
out.append('from typing import Dict, Any, List, Optional\n')
out.append('from sqlalchemy.orm import Session\n')
out.append('from sqlalchemy import text\n\n')
out.append('from reins.api.solutions_shared import _serialize, _parse_json_field, _row_to_solution\n\n')
out.append('logger = logging.getLogger(__name__)\n\n')

# compare_solutions: lines 672-691 (0-idx 671-690)
# But it's INSIDE the file, so let me read from the right range
# The scoring helpers (_safe_float, _extract_metric, _normalize) are NESTED inside compare_solutions
# So we need to copy the whole compare_solutions function including nested helpers
# Lines 672-691 = the function signature + docstring
# The body starts at 692

# Find compare_solutions start and end
comp_start = None
comp_end = None
for i, line in enumerate(L):
    if line.strip().startswith('def compare_solutions('):
        comp_start = i
    elif comp_start is not None and (line.strip().startswith('def ') or line.strip().startswith('class ')) and i > comp_start:
        comp_end = i
        break

print(f"compare_solutions: lines {comp_start+1}-{comp_end+1}")
for i in range(comp_start, comp_end):
    out.append(L[i])
out.append('\n')

# adjust_constraints_for_next_round: lines 874-932
adj_start = None
adj_end = None
for i, line in enumerate(L):
    if line.strip().startswith('def adjust_constraints_for_next_round('):
        adj_start = i
    elif adj_start is not None and i > adj_start and (line.strip().startswith('def ') or line.strip().startswith('class ')):
        adj_end = i
        break

if adj_end:
    print(f"adjust_constraints: lines {adj_start+1}-{adj_end+1}")
    for i in range(adj_start, adj_end):
        out.append(L[i])
else:
    print(f"adjust_constraints: lines {adj_start+1}-END")
    for i in range(adj_start, len(L)):
        out.append(L[i])

open(os.path.join(DIR, 'solutions_helpers.py'), 'w', encoding='utf-8').writelines(out)
print(f"solutions_helpers.py: {len(out)} lines")
