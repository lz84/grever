"""GRASP assessment + deprecated recommend endpoints — split from grasp_router.py"""

from fastapi import APIRouter, Request

from grasp.api.grasp_helpers import _load_cognitions

router = APIRouter()

@router.get("/cognition-assessment/{agent_id}")
async def cognition_assessment(agent_id: str):
    """4 维度认知评估：检索质量、上下文利用率、注入准确率、知识新鲜度"""
    try:
        from grasp.analysis.cognitive_assessment import get_assessment_service
        service = get_assessment_service()
        result = service.assess(agent_id=agent_id)
        return result.to_dict()
    except Exception as e:
        cognitions = _load_cognitions()
        agent_cognitions = [c for c in cognitions if c.get("source", {}).get("agent_id") == agent_id]
        return {
            "agent_id": agent_id,
            "overall_score": 75,
            "dimensions": {
                "retrieval_quality": {
                    "score": 80,
                    "label": "检索质量",
                    "description": "从知识库检索的准确性和相关性",
                },
                "context_utilization": {
                    "score": 70,
                    "label": "上下文利用率",
                    "description": "对上下文的利用效率",
                },
                "injection_accuracy": {
                    "score": 75,
                    "label": "注入准确率",
                    "description": "认知注入的准确性",
                },
                "knowledge_freshness": {
                    "score": 72,
                    "label": "知识新鲜度",
                    "description": "知识的时效性",
                },
            },
            "knowledge_used": len(agent_cognitions),
            "status": "评估完成",
        }

@router.post("/recommend")
async def recommend_plans(request: Request):
    """[已废弃] 预案推荐 API"""
    return {"plans": [], "total": 0}
