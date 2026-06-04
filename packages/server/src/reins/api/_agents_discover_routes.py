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
    # AgentInfo.to_dict() 输出 capabilities，前端需要 capability_tags
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


# === Agent Matching (merged from agent_matching.py) ===
"""
Agent 匹配 API 路由
Sprint 23: Agent 自动匹配 + Scenario trust_level 计算
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/agent-matching", tags=["agent-matching"])

class MatchRequest(BaseModel):
    scenario_id: str

class AgentMatchResponse(BaseModel):
    role: str
    required_capabilities: List[str]
    matched_agents: List[Dict]
    missing: int

@router.post("/match")
def match_agents(req: MatchRequest):
    """根据 Scenario 匹配 Agent"""
    try:
        from reins.common.database import get_db_manager
        from sqlalchemy import text
        import json
        
        engine = get_db_manager().engine
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT agent_requirements FROM scenarios WHERE id = :id"
            ), {"id": req.scenario_id}).fetchone()
        
        if not row or not row.agent_requirements:
            raise HTTPException(404, f"Scenario {req.scenario_id} not found or no requirements")
        
        requirements = json.loads(row.agent_requirements) if isinstance(row.agent_requirements, str) else row.agent_requirements
        
        from reins.scheduler.assigner.agent_matcher import match_agents_for_scenario
        results = match_agents_for_scenario(requirements)
        
        return [{
            "role": r.role,
            "required_capabilities": r.required_capabilities,
            "matched_agents": r.matched_agents,
            "missing": r.missing
        } for r in results]
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Match failed: {str(e)}")

@router.post("/trust-levels/update")
def update_trust_levels():
    """批量更新所有 Scenario 的 trust_level"""
    from reins.scheduler.assigner.agent_matcher import update_all_trust_levels
    update_all_trust_levels()
    return {"success": True}

@router.get("/trust-levels/{scenario_id}")
def get_trust_level(scenario_id: str):
    """获取单个 Scenario 的 trust_level"""
    from reins.scheduler.assigner.agent_matcher import calculate_trust_level
    level = calculate_trust_level(scenario_id)
    return {"scenario_id": scenario_id, "trust_level": level}
