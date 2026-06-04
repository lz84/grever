"""
Shared models and utilities for scenario_workflow submodules.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict
import json

MATCH_THRESHOLD = 0.30

class ScenarioMatchItem(BaseModel):
    scenario_id: str
    name: str
    category: str
    level: str
    match_score: float
    trust_level: str
    usage_count: int
    description: str
    phase_count: int

class ScenarioMatchResponse(BaseModel):
    goal_id: str
    goal_title: str
    matches: List[ScenarioMatchItem]
    threshold_met: bool
    threshold: float

class MatchPreviewRequest(BaseModel):
    title: str
    description: Optional[str] = None

class MatchPreviewResponse(BaseModel):
    title: str
    matches: List[ScenarioMatchItem]
    threshold_met: bool
    threshold: float

class InstantiateWorkflowRequest(BaseModel):
    goal_id: Optional[str] = None

class InstantiateWorkflowResponse(BaseModel):
    workflow_id: str
    scenario_id: str
    goal_id: str
    name: str
    status: str
    phase_count: int
    dag: Dict

class CreateScenarioResponse(BaseModel):
    scenario_id: str
    name: str
    category: str
    description: str
    phase_count: int

class EmergencyStartupRequest(BaseModel):
    goal_id: str
    scenario_id: Optional[str] = None
    priority: str = "critical"
    description: Optional[str] = None

class EmergencyStartupResponse(BaseModel):
    success: bool
    goal_id: str
    scenario_id: str
    workflow_id: str
    status: str
    tasks_created: int
    task_ids: List[str]
    phases: List[Dict]
    execution_description: str
    activated_at: str
    message: str

class CommandCenterRequest(BaseModel):
    goal_id: str
    location: Optional[str] = None
    commander_agent_id: Optional[str] = None
    description: Optional[str] = None

class CommandCenterResponse(BaseModel):
    success: bool
    goal_id: str
    command_center_id: str
    commander_agent_id: str
    status: str
    members: List[Dict]
    capabilities: List[str]
    communication_channels: Dict
    execution_description: str
    established_at: str
    message: str

def _parse_json(val):
    if val is None:
        return None
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return None
    return val
