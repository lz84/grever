# -*- coding: utf-8 -*-
"""
Goal mode-switching endpoint.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from reins.common.database import get_db
from models.goal import Goal
from reins.api.goals_research_models import SetGoalModeRequest

router = APIRouter(prefix="/api/v1/goals", tags=["goals-exploration"])

@router.post("/{goal_id}/mode")
def set_goal_mode(goal_id: str, req: SetGoalModeRequest, db: Session = Depends(get_db)):
    """切换目标模式"""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()

    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    if req.mode not in ("engineering", "research"):
        raise HTTPException(
            status_code=400,
            detail="mode 只支持 engineering（工程模式）或 research（研究模式）"
        )

    goal.mode = req.mode
    goal.updated_at = datetime.utcnow()
    if req.optimization_target is not None:
        goal.optimization_target = req.optimization_target
    if req.convergence_threshold is not None:
        goal.convergence_threshold = req.convergence_threshold
    if req.max_rounds is not None:
        goal.max_rounds = req.max_rounds
    if req.diversity is not None:
        goal.diversity = req.diversity
    if req.portfolio_size is not None:
        goal.portfolio_size = req.portfolio_size

    db.commit()

    return {"goal_id": goal_id, "mode": req.mode, "updated": True}
