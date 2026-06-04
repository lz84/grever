"""Goals API: Pydantic request models."""
from pydantic import BaseModel

class SetGoalVerifierRequest(BaseModel):
    """设置目标验证 Agent 请求"""
    verifier_agent_id: str
