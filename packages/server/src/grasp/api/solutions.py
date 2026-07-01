# -*- coding: utf-8 -*-
"""solutions.py - facade"""
from fastapi import APIRouter
router = APIRouter(prefix="/api/v1", tags=["solutions"])

from grasp.api import solutions_shared, solutions_convergence, solutions_helpers
from grasp.api import solutions_crud, solutions_consensus, solutions_iteration_helpers
from grasp.api import solutions_extraction, solutions_discussion, solutions_iteration

router.include_router(solutions_shared.router)
router.include_router(solutions_convergence.router)
router.include_router(solutions_helpers.router)
router.include_router(solutions_crud.router)
router.include_router(solutions_consensus.router)
router.include_router(solutions_iteration_helpers.router)
router.include_router(solutions_extraction.router)
router.include_router(solutions_discussion.router)
router.include_router(solutions_iteration.router)

# Re-export functions needed by goals_exploration_iteration.py
from grasp.api.solutions_shared import (
    auto_capture_solution,
    compare_solutions,
    adjust_constraints_for_next_round,
)
