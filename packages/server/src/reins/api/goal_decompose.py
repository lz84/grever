"""
目标自动分解 API — Facade

MAK-226: 目标自动分解 + Grasp 认知注入
子模块:
  - goal_decompose_helpers: 辅助函数与提示词
  - goal_decompose_preview: 预览端点
  - goal_decompose_submit: 提交端点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.goal import Goal
from reins.common.database import get_db
from .goal_decompose_preview import router as preview_router
from .goal_decompose_submit import router as submit_router
from reins.api.goals_models import SetGoalVerifierRequest

router = APIRouter(prefix="/api/v1/goals", tags=["goals"])
router.include_router(preview_router)
router.include_router(submit_router)

@router.post("/{goal_id}/verifier")
def set_goal_verifier(goal_id: str, request: SetGoalVerifierRequest, db: Session = Depends(get_db)):
    """设置 Goal 的验证 Agent ID"""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal.verifier_agent_id = request.verifier_agent_id
    goal.updated_at = int(__import__('datetime').datetime.now().timestamp())
    db.commit()
    db.refresh(goal)

    return {"goal_id": goal_id, "verifier_agent_id": request.verifier_agent_id}
