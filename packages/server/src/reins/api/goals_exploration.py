# -*- coding: utf-8 -*-
"""Goals Exploration — Facade (2026-05-14 重构)"""
from fastapi import APIRouter
from reins.api.goals_exploration_mode import router as mode_router
from reins.api.goals_exploration_lifecycle import router as lifecycle_router
from reins.api.goals_exploration_iteration import router as iteration_router

router = APIRouter()
for _r in [mode_router, lifecycle_router, iteration_router]:
    for route in _r.routes:
        router.routes.append(route)
