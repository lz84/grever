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
from sqlalchemy import text

from reins.common.database import get_db
from .goals_exploration_models import (
    StartIterationRequest,
    IterateRequest,
)
from .goals_exploration_helpers import _check_convergence

router = APIRouter(prefix="/api/v1/goals", tags=["goals-exploration"])

@router.post("/{goal_id}/start-iteration")
def start_iteration(goal_id: str, req: StartIterationRequest = Body(default=None), db: Session = Depends(get_db)):
    """启动迭代回路"""
    row = db.execute(
        text("SELECT id, mode FROM goals WHERE id = :id"),
        {"id": goal_id}
    ).mappings().fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Goal not found")

    db.execute(
        text("UPDATE goals SET mode = 'optimization', run_status = 'running', updated_at = :now WHERE id = :id"),
        {"now": datetime.utcnow().isoformat(), "id": goal_id}
    )
    db.commit()

    if req and req.initial_constraints:
        ic_id = f"ic-{uuid.uuid4().hex[:12]}"
        db.execute(
            text("""
                INSERT INTO iteration_constraints (id, goal_id, round, constraints, reason, created_by, created_at)
                VALUES (:id, :goal_id, 1, :constraints, :reason, :created_by, :created_at)
            """),
            {
                "id": ic_id,
                "goal_id": goal_id,
                "round": 1,
                "constraints": json.dumps(req.initial_constraints, ensure_ascii=False),
                "reason": "Iteration started",
                "created_by": "system",
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        db.commit()

    return {
        "goal_id": goal_id,
        "mode": "optimization",
        "run_status": "running",
        "round": 1,
        "status": "started",
    }

@router.get("/{goal_id}/iteration-status")
def iteration_status(goal_id: str, db: Session = Depends(get_db)):
    """获取迭代状态"""
    goal_row = db.execute(
        text("SELECT id, mode, run_status, optimization_target, convergence_threshold, max_rounds FROM goals WHERE id = :id"),
        {"id": goal_id}
    ).mappings().fetchone()

    if not goal_row:
        raise HTTPException(status_code=404, detail="Goal not found")

    total_solutions = db.execute(
        text("SELECT COUNT(*) as cnt FROM solutions WHERE goal_id = :gid"),
        {"gid": goal_id}
    ).fetchone()[0]

    current_round = db.execute(
        text("SELECT COALESCE(MAX(round), 0) FROM solutions WHERE goal_id = :gid"),
        {"gid": goal_id}
    ).fetchone()[0]

    optimal_row = db.execute(
        text("SELECT id, name, score FROM solutions WHERE goal_id = :gid AND is_optimal = 1 ORDER BY score DESC LIMIT 1"),
        {"gid": goal_id}
    ).mappings().fetchone()

    return {
        "goal_id": goal_id,
        "mode": goal_row.get("mode", "normal"),
        "run_status": goal_row.get("run_status", "idle"),
        "current_round": current_round,
        "max_rounds": goal_row.get("max_rounds", 10),
        "convergence_threshold": goal_row.get("convergence_threshold", 0.05),
        "optimization_target": goal_row.get("optimization_target"),
        "total_solutions": total_solutions,
        "optimal_solution": {
            "id": optimal_row.get("id"),
            "name": optimal_row.get("name"),
            "score": optimal_row.get("score"),
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

    goal_row = db.execute(
        text("SELECT id, mode, convergence_threshold, max_rounds FROM goals WHERE id = :id"),
        {"id": goal_id}
    ).mappings().fetchone()

    if not goal_row:
        raise HTTPException(status_code=404, detail="Goal not found")

    current_round = db.execute(
        text("SELECT COALESCE(MAX(round), 0) FROM solutions WHERE goal_id = :gid"),
        {"gid": goal_id}
    ).fetchone()[0]

    max_rounds = goal_row.get("max_rounds", 10)
    next_round = current_round + 1

    if next_round > max_rounds:
        db.execute(
            text("UPDATE goals SET run_status = 'converged', updated_at = :now WHERE id = :id"),
            {"now": datetime.utcnow().isoformat(), "id": goal_id}
        )
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

    db.execute(
        text("UPDATE goals SET run_status = :status, updated_at = :now WHERE id = :id"),
        {"status": new_status, "now": datetime.utcnow().isoformat(), "id": goal_id}
    )
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
    rows = db.execute(
        text("""
            SELECT * FROM iteration_constraints WHERE goal_id = :gid
            ORDER BY round ASC, created_at ASC
        """),
        {"gid": goal_id}
    ).mappings().fetchall()

    def _parse(row):
        constraints_raw = row.get("constraints")
        if constraints_raw and isinstance(constraints_raw, str):
            try:
                constraints = json.loads(constraints_raw)
            except (json.JSONDecodeError, TypeError):
                constraints = constraints_raw
        else:
            constraints = constraints_raw
        return {
            "id": row.get("id"),
            "round": row.get("round"),
            "constraints": constraints,
            "reason": row.get("reason"),
            "created_by": row.get("created_by"),
            "created_at": row.get("created_at"),
        }

    return {
        "goal_id": goal_id,
        "constraints_history": [_parse(r) for r in rows],
        "total_rounds": len(rows),
    }

@router.post("/{goal_id}/pause-iteration")
def pause_iteration(goal_id: str, db: Session = Depends(get_db)):
    """暂停迭代"""
    goal_row = db.execute(
        text("SELECT id, mode FROM goals WHERE id = :id"),
        {"id": goal_id}
    ).mappings().fetchone()

    if not goal_row:
        raise HTTPException(status_code=404, detail="Goal not found")

    db.execute(
        text("UPDATE goals SET run_status = 'paused', updated_at = :now WHERE id = :id"),
        {"now": datetime.utcnow().isoformat(), "id": goal_id}
    )
    db.commit()

    return {
        "goal_id": goal_id,
        "status": "paused",
        "message": "迭代已暂停",
    }

@router.post("/{goal_id}/converge-iteration")
def converge_iteration(goal_id: str, db: Session = Depends(get_db)):
    """宣布收敛（标记为最优方案）"""
    goal_row = db.execute(
        text("SELECT id, mode FROM goals WHERE id = :id"),
        {"id": goal_id}
    ).mappings().fetchone()

    if not goal_row:
        raise HTTPException(status_code=404, detail="Goal not found")

    best_row = db.execute(
        text("SELECT id, score FROM solutions WHERE goal_id = :gid ORDER BY score DESC LIMIT 1"),
        {"gid": goal_id}
    ).mappings().fetchone()

    if best_row:
        db.execute(
            text("UPDATE solutions SET is_optimal = 1, updated_at = :now WHERE id = :id"),
            {"now": datetime.utcnow().isoformat(), "id": best_row.get("id")}
        )
        db.commit()

    db.execute(
        text("UPDATE goals SET run_status = 'converged', updated_at = :now WHERE id = :id"),
        {"now": datetime.utcnow().isoformat(), "id": goal_id}
    )
    db.commit()

    return {
        "goal_id": goal_id,
        "status": "converged",
        "optimal_solution_id": best_row.get("id") if best_row else None,
    }