"""Split solutions_iteration.py and solutions_exploration.py"""
import os

DIR = r"D:\work\research\agents-nexus\packages\server\src\reins\api"

# ================================================================
# Split solutions_iteration.py (837 lines)
# Iteration helpers (Pydantic models + helper functions) → iteration_helpers.py
# Iteration endpoints → solutions_iteration.py
# ================================================================
L = open(os.path.join(DIR, 'solutions_iteration.py'), encoding='utf-8').readlines()

# Find first @router line
first_router = None
for i, line in enumerate(L):
    if '@router.' in line:
        first_router = i
        break

print(f"Iteration: {len(L)} lines, first router at line {first_router+1}")

# helpers: lines 0 to first_router
helpers = []
helpers.append('# -*- coding: utf-8 -*-\n')
helpers.append('"""Iteration helpers: models and functions."""\n\n')
for i in range(1, first_router):  # skip duplicate header
    helpers.append(L[i])

open(os.path.join(DIR, 'solutions_iteration_helpers.py'), 'w', encoding='utf-8').writelines(helpers)
print(f"iteration_helpers.py: {len(helpers)} lines")

# endpoints: lines 0 to first_router + endpoints
endpoints = []
endpoints.append('# -*- coding: utf-8 -*-\n')
endpoints.append('"""Iteration endpoints."""\n\n')
endpoints.append('from reins.api.solutions_iteration_helpers import *\n\n')
for i in range(first_router, len(L)):
    endpoints.append(L[i])

open(os.path.join(DIR, 'solutions_iteration.py'), 'w', encoding='utf-8').writelines(endpoints)
print(f"solutions_iteration.py: {len(endpoints)} lines")

# ================================================================
# Split solutions_exploration.py (550 lines)
# Part 1: auto_capture + _track → exploration_auto.py (~280 lines)
# Part 2: check_convergence + extract + compare_auto + convergence_check → exploration_conv.py (~270 lines)
# ================================================================
L2 = open(os.path.join(DIR, 'solutions_exploration.py'), encoding='utf-8').readlines()
print(f"\nExploration: {len(L2)} lines")

# Find where check_convergence starts
conv_start = None
for i, line in enumerate(L2):
    if line.strip().startswith('def check_convergence('):
        conv_start = i
        break

print(f"check_convergence at line {conv_start+1}")

# Part 1: auto_capture stuff
part1 = []
part1.append('# -*- coding: utf-8 -*-\n')
part1.append('"""Auto-capture: capture solutions on task completion."""\n\n')
for i in range(1, conv_start):  # skip duplicate header
    part1.append(L2[i])

open(os.path.join(DIR, 'solutions_exploration.py'), 'w', encoding='utf-8').writelines(part1)
print(f"exploration.py (part1): {len(part1)} lines")

# Part 2: convergence stuff
part2 = []
part2.append('# -*- coding: utf-8 -*-\n')
part2.append('"""Convergence detection and comparison."""\n\n')
for i in range(conv_start, len(L2)):
    part2.append(L2[i])

open(os.path.join(DIR, 'solutions_convergence.py'), 'w', encoding='utf-8').writelines(part2)
print(f"solutions_convergence.py (part2): {len(part2)} lines")

# Update solutions.py to import from both
SRC = os.path.join(DIR, 'solutions.py')
sol_lines = open(SRC, encoding='utf-8').readlines()
new_lines = []
for line in sol_lines:
    if 'from reins.api.solutions_exploration import' in line:
        new_lines.append('from reins.api.solutions_exploration import auto_capture_solution, _track_convergence_streak\n')
        new_lines.append('from reins.api.solutions_convergence import check_convergence, extract_parameters_from_result, compare_solutions_auto, convergence_check\n')
    elif 'solutions_iteration_helpers' in line:
        pass  # skip, it's imported in iteration module
    else:
        new_lines.append(line)

open(SRC, 'w', encoding='utf-8').writelines(new_lines)
print(f"\nsolutions.py updated: {len(new_lines)} lines")
print("\nDone!")
