"""Split goals_exploration.py"""
import os

SRC = r"D:\work\research\agents-nexus\packages\server\src\reins\api\goals_exploration.py"
DIR = os.path.dirname(SRC)
L = open(SRC, encoding='utf-8').readlines()
N = len(L)

# Find function boundaries
# Lines 1-83: setup (imports + class + prompt)
# explore_goal starts at ~85
# quick_explore_goal starts at ~290
# get_exploration_status starts at ~410
# get_exploration_scenarios starts at ~505
# stop_exploration starts at ~600

# Split:
# 1. goals_exploration_shared.py: setup + models + prompt (lines 0-84 = ~85 lines)
# 2. goals_exploration_explore.py: explore_goal + quick_explore_goal + helpers (lines 85-409 = ~325 lines)
# 3. goals_exploration_status.py: 3 remaining endpoints (lines 410-699 = ~290 lines)
# 4. goals_exploration.py: facade

setup_end = 84  # 0-indexed
explore_end = 409  # 0-indexed (before get_exploration_status)

# 1. goals_exploration_shared.py
shared = L[:setup_end+1]
shared_lines = [
    '# -*- coding: utf-8 -*-\n',
    '"""Goals Exploration — shared setup (models, prompts)."""\n\n',
    'import uuid, logging, re\n',
    'from datetime import datetime\n',
    'from typing import Optional, List, Dict, Any\n',
    'from fastapi import APIRouter, Depends, HTTPException, status, Query\n',
    'from sqlalchemy.orm import Session\n',
    'from sqlalchemy import text\n\n',
    'from reins.database import get_db\n\n',
    'router = __import__("fastapi").APIRouter(prefix="/api/v1", tags=["goals"])\n\n',
]
# Find class/func in setup
for i, line in enumerate(L[:setup_end+1]):
    if 'class ' in line or 'def ' in line or '_EXPLORATION' in line:
        for j in range(i, setup_end+1):
            shared_lines.append(L[j])
        break

open(os.path.join(DIR, 'goals_exploration_shared.py'), 'w', encoding='utf-8').writelines(shared_lines)
print(f"shared: {len(shared_lines)} lines")

# 2. goals_exploration_explore.py
explore = [
    '# -*- coding: utf-8 -*-\n',
    '"""Goals Exploration — main explore endpoints."""\n\n',
    'from reins.api.goals_exploration_shared import router\n\n',
]
for i in range(85, explore_end+1):
    explore.append(L[i])

open(os.path.join(DIR, 'goals_exploration_explore.py'), 'w', encoding='utf-8').writelines(explore)
print(f"explore: {len(explore)} lines")

# 3. goals_exploration_status.py  
status_ep = [
    '# -*- coding: utf-8 -*-\n',
    '"""Goals Exploration — status and control endpoints."""\n\n',
    'from reins.api.goals_exploration_shared import router\n\n',
]
for i in range(explore_end+1, N):
    status_ep.append(L[i])

open(os.path.join(DIR, 'goals_exploration_status.py'), 'w', encoding='utf-8').writelines(status_ep)
print(f"status: {len(status_ep)} lines")

# 4. facade
facade = [
    '# -*- coding: utf-8 -*-\n',
    '"""Goals Exploration — Facade (2026-05-14 重构)"""\n\n',
    'from fastapi import APIRouter\n',
    'from reins.api.goals_exploration_shared import router as shared_router\n',
    'from reins.api.goals_exploration_explore import router as explore_router\n',
    'from reins.api.goals_exploration_status import router as status_router\n\n',
    'router = APIRouter()\n',
    'for _r in [shared_router, explore_router, status_router]:\n',
    '    for route in _r.routes:\n',
    '        router.routes.append(route)\n',
]

open(os.path.join(DIR, 'goals_exploration.py'), 'w', encoding='utf-8').writelines(facade)
print(f"facade: {len(facade)} lines")
print("Done!")
