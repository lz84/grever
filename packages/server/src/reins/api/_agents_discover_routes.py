"""Agent discovery routes."""
import json
from loguru import logger
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from api.app_state import get_reins
from reins.api._agents_register_routes import AgentResponse

router = APIRouter()

def _enrich_agent_dict(a) -> dict:
    """将 DB AgentInfo 转为前端 AgentResponse 兼容格式，补上 capability_tags。"""
    import json
    d = a.to_dict()
    caps_raw = d.pop('capabilities', {})
    if isinstance(caps_raw, dict):
        d['capability_tags'] = caps_raw
    elif isinstance(caps_raw, list):
        d['capability_tags'] = {"business": [], "professional": [], "technical": caps_raw, "management": []}
    else:
        d['capability_tags'] = {}
    d.setdefault('trigger_mode', 'sse')
    d.setdefault('poll_interval_seconds', 10)
    return d

@router.get("/discover", response_model=List[AgentResponse])
def discover_agents(
    capabilities: Optional[List[str]] = None,
    status: Optional[str] = None,
    max_load: Optional[int] = None,
):
    """发现 Agent"""
    reins = get_reins()
    from models import AgentStatus
    status_enum = AgentStatus(status) if status else None
    agents = reins.discover_agents(capabilities, status_enum, max_load)
    return [AgentResponse.model_validate(_enrich_agent_dict(a)) for a in agents]

@router.get("/discover/{agent_id}", response_model=AgentResponse)
def find_agent(agent_id: str):
    """查找特定 Agent"""
    reins = get_reins()
    a = reins.find_agent(agent_id)
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse.model_validate(_enrich_agent_dict(a))
