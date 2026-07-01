# -*- coding: utf-8 -*-
"""
Goal iteration-mode endpoints.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import func

from reins.common.database import get_db
from models import Goal, Solution, IterationConstraint
from .goals_research_models import (
    StartIterationRequest,
    IterateRequest,
)
from .goals_research_helpers import _check_convergence

router = APIRouter(prefix="/api/v1/goals", tags=["goals-exploration"])


@router.post("/{goal_id}/start-iteration")
def start_iteration(goal_id: str, req: StartIterationRequest = Body(default=None), db: Session = Depends(get_db)):
    """启动迭代回路"""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Engineering 模式不允许迭代
    if goal.mode == "engineering":
        raise HTTPException(status_code=400, detail="Engineering mode goals cannot use iteration. Use /activate instead.")

    # 支持 diversity 参数覆盖
    if req and req.diversity is not None:
        goal.diversity = req.diversity
    elif not goal.diversity:
        goal.diversity = 'best'

    # Only set diversity if provided
    goal.run_status = 'running'
    goal.updated_at = datetime.utcnow().isoformat()
    db.commit()

    if req and req.initial_constraints:
        ic = IterationConstraint(
            id=f"ic-{uuid.uuid4().hex[:12]}",
            goal_id=goal_id,
            round=1,
            constraints=json.dumps(req.initial_constraints, ensure_ascii=False),
            reason="Iteration started",
            created_by="system",
            created_at=datetime.utcnow().isoformat(),
        )
        db.add(ic)
        db.commit()

    return {
        "goal_id": goal_id,
        "mode": goal.mode or "research",
        "run_status": "running",
        "diversity": goal.diversity or "best",
        "round": 1,
        "status": "started"
    }


@router.get("/{goal_id}/iteration-status")
def iteration_status(goal_id: str, db: Session = Depends(get_db)):
    """获取迭代状态"""
    goal_row = db.query(Goal).with_entities(
        Goal.id, Goal.mode, Goal.run_status, Goal.diversity,
        Goal.optimization_target, Goal.convergence_threshold, Goal.max_rounds,
    ).filter(Goal.id == goal_id).first()

    if not goal_row:
        raise HTTPException(status_code=404, detail="Goal not found")

    total_solutions = db.query(func.count(Solution.id)).filter(Solution.goal_id == goal_id).scalar()

    current_round = db.query(func.coalesce(func.max(Solution.round), 0)).filter(
        Solution.goal_id == goal_id
    ).scalar()

    optimal_row = db.query(Solution).with_entities(
        Solution.id, Solution.name, Solution.score
    ).filter(
        Solution.goal_id == goal_id,
        Solution.is_optimal == True,
    ).order_by(Solution.score.desc()).first()

    return {
        "goal_id": goal_id,
        "mode": goal_row[1] or "engineering",
        "run_status": goal_row[2] or "idle",
        "diversity": goal_row[3] or "best",
        "current_round": current_round,
        "max_rounds": goal_row[6] or 10,
        "convergence_threshold": goal_row[5] or 0.05,
        "optimization_target": goal_row[4],
        "total_solutions": total_solutions,
        "optimal_solution": {
            "id": optimal_row[0],
            "name": optimal_row[1],
            "score": optimal_row[2],
        } if optimal_row else None,
    }


@router.post("/{goal_id}/iterate")
def trigger_iteration(goal_id: str, req: IterateRequest = Body(default=None), db: Session = Depends(get_db)):
    """触发下一轮完整迭代回路"""
    from grasp.api.solutions import (
        auto_capture_solution,
        compare_solutions,
        adjust_constraints_for_next_round,
    )

    goal_row = db.query(Goal).with_entities(
        Goal.id, Goal.mode, Goal.diversity, Goal.convergence_threshold, Goal.max_rounds,
    ).filter(Goal.id == goal_id).first()

    if not goal_row:
        raise HTTPException(status_code=404, detail="Goal not found")

    current_round = db.query(func.coalesce(func.max(Solution.round), 0)).filter(
        Solution.goal_id == goal_id
    ).scalar()

    max_rounds = goal_row[4] or 10
    next_round = current_round + 1

    # 支持 diversity 参数覆盖
    if req and req.diversity is not None:
        db.query(Goal).filter(Goal.id == goal_id).update({"diversity": req.diversity})
        db.commit()

    if next_round > max_rounds:
        db.query(Goal).filter(Goal.id == goal_id).update({
            "run_status": 'converged',
            "updated_at": datetime.utcnow().isoformat(),
        })
        db.commit()
        return {
            "goal_id": goal_id,
            "status": "max_rounds_reached",
            "current_round": current_round,
            "max_rounds": max_rounds,
            "run_status": "converged",
            "message": f"已达到最大轮次 {max_rounds}，迭代结束",
        }

    auto_cap_result = auto_capture_solution(goal_id, db)
    auto_captured = auto_cap_result is not None

    compare_result = compare_solutions(goal_id, db)
    scored_count = compare_result.get("updated", 0)

    convergence_result = _check_convergence(db, goal_id, current_round)

    constraint_result = adjust_constraints_for_next_round(goal_id, db)
    adjusted_constraints = constraint_result.get("new_constraints", {}) if constraint_result else {}

    cr = convergence_result
    if cr.get("done"):
        new_status = "done"
    elif cr.get("requires_human"):
        new_status = "requires_human"
    elif cr.get("converged"):
        new_status = "converged"
    else:
        new_status = "waiting_next_round"

    db.query(Goal).filter(Goal.id == goal_id).update({
        "run_status": new_status,
        "updated_at": datetime.utcnow().isoformat(),
    })
    db.commit()

    return {
        "goal_id": goal_id,
        "status": "iterated",
        "current_round": current_round,
        "next_round": next_round,
        "auto_captured": auto_captured,
        "solutions_scored": scored_count,
        "convergence": convergence_result,
        "adjusted_constraints": adjusted_constraints,
        "run_status": new_status,
        "message": f"第 {next_round} 轮迭代准备就绪",
    }


@router.get("/{goal_id}/constraints")
def constraint_history(goal_id: str, db: Session = Depends(get_db)):
    """查看约束历史"""
    rows = db.query(IterationConstraint).filter(
        IterationConstraint.goal_id == goal_id
    ).order_by(IterationConstraint.round.asc(), IterationConstraint.created_at.asc()).all()

    def _parse(c: IterationConstraint):
        constraints_raw = c.constraints
        if constraints_raw and isinstance(constraints_raw, str):
            try:
                constraints = json.loads(constraints_raw)
            except (json.JSONDecodeError, TypeError):
                constraints = constraints_raw
        else:
            constraints = constraints_raw
        return {
            "id": c.id,
            "round": c.round,
            "constraints": constraints,
            "reason": c.reason,
            "created_by": c.created_by,
            "created_at": c.created_at,
        }

    return {
        "goal_id": goal_id,
        "constraints_history": [_parse(r) for r in rows],
        "total_rounds": len(rows),
    }


@router.post("/{goal_id}/pause-iteration")
def pause_iteration(goal_id: str, db: Session = Depends(get_db)):
    """暂停迭代"""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal.run_status = 'paused'
    goal.updated_at = datetime.utcnow().isoformat()
    db.commit()

    return {
        "goal_id": goal_id,
        "status": "paused",
        "message": "迭代已暂停",
    }


@router.post("/{goal_id}/converge-iteration")
def converge_iteration(goal_id: str, db: Session = Depends(get_db)):
    """宣布收敛（标记为最优方案）"""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    best = db.query(Solution).filter(
        Solution.goal_id == goal_id
    ).order_by(Solution.score.desc()).first()

    if best:
        best.is_optimal = True
        best.updated_at = datetime.utcnow()
        db.commit()

    goal.run_status = 'converged'
    goal.updated_at = datetime.utcnow().isoformat()
    db.commit()

    return {
        "goal_id": goal_id,
        "status": "converged",
        "optimal_solution_id": best.id if best else None,
    }
