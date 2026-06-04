"""
Scenario Workflow API — Consolidated from sub-modules.

Contains: match, create, instantiate, emergency.
"""
from fastapi import APIRouter

from .scenario_match import router as scenario_match_router
from .scenario_instantiate import router as scenario_instantiate_router
from .scenario_models import (
    MATCH_THRESHOLD,
    ScenarioMatchItem,
    ScenarioMatchResponse,
    MatchPreviewRequest,
    MatchPreviewResponse,
    InstantiateWorkflowRequest,
    InstantiateWorkflowResponse,
    CreateScenarioResponse,
)

router = APIRouter(tags=["scenario-workflow"])
router.include_router(scenario_match_router)
router.include_router(scenario_instantiate_router)

