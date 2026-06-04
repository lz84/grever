# -*- coding: utf-8 -*-
"""
Goal mode-switching endpoint.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from reins.common.database import get_db
from .goals_exploration_models import SetGoalModeRequest

router = APIRouter(prefix="/api/v1/goals", tags=["goals-exploration"])

@router.post("/{goal_id}/mode")
def set_goal_mode(goal_id: str, req: SetGoalModeRequest, db: Session = Depends(get_db)):
    """切换目标模式"""
    row = db.execute(
        text("SELECT id FROM goals WHERE id = :id"),
        {"id": goal_id}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Goal not found")

    if req.mode not in ("normal", "exploration", "optimization"):
        raise HTTPException(
            status_code=400,
            detail="mode must be one of: normal, exploration, optimization"
        )

    updates = {
        "mode": req.mode,
        "updated_at": datetime.utcnow().isoformat(),
    }
    if req.optimization_target is not None:
        updates["optimization_target"] = req.optimization_target
    if req.convergence_threshold is not None:
        updates["convergence_threshold"] = req.convergence_threshold
    if req.max_rounds is not None:
        updates["max_rounds"] = req.max_rounds

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    db.execute(
        text(f"UPDATE goals SET {set_clause} WHERE id = :id"),
        {**updates, "id": goal_id}
    )
    db.commit()

    return {"goal_id": goal_id, "mode": req.mode, "updated": True}