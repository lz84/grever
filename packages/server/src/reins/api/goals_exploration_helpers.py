# -*- coding: utf-8 -*-
"""
Helper functions for goals exploration mode.
"""

import json
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

def _check_convergence(db: Session, goal_id: str, current_round: int) -> Dict[str, Any]:
    """
    判断收敛状态（探索 vs 优化模式规则不同）

    探索模式规则：
      - 改进 < 5% → requires_human=True（需要人工介入）
      - 改进 >= 5% → requires_human=False，继续自动迭代

    优化模式规则：
      - score >= 90 → done（目标达成）
      - 改进 < 1% → converged=True（已收敛）
      - 改进 >= 1% → converged=False（继续迭代）

    通用规则：
      - 只有 1 个方案 → 不收敛
      - 达到最大轮次 → converged=True
    """
    goal_row = db.execute(
        text("SELECT mode, convergence_threshold, max_rounds FROM goals WHERE id = :id"),
        {"id": goal_id}
    ).mappings().fetchone()

    if not goal_row:
        return {"should_converge": False, "requires_human": False, "reason": "goal not found"}

    mode = goal_row.get("mode", "normal")
    threshold = goal_row.get("convergence_threshold", 0.05) or 0.05
    max_rounds = goal_row.get("max_rounds", 10) or 10

    # 只有 1 个方案 → 不收敛
    total = db.execute(
        text("SELECT COUNT(*) FROM solutions WHERE goal_id = :gid"),
        {"gid": goal_id}
    ).fetchone()[0]
    if total < 2:
        return {
            "requires_human": False,
            "converged": False,
            "done": False,
            "reason": "not enough solutions",
            "latest_score": None,
            "improvement": None,
        }

    # 达到最大轮次 → 收敛
    if current_round >= max_rounds:
        return {
            "requires_human": False,
            "converged": True,
            "done": False,
            "reason": f"reached max rounds ({max_rounds})",
        }

    # 获取最近 2 轮的评分
    solutions = db.execute(
        text("""
            SELECT round, score FROM solutions
            WHERE goal_id = :gid AND score IS NOT NULL
            ORDER BY round DESC
        """),
        {"gid": goal_id}
    ).mappings().fetchall()

    if len(solutions) < 2:
        return {
            "requires_human": False,
            "converged": False,
            "done": False,
            "reason": "not enough scored solutions",
            "latest_score": None,
            "improvement": None,
        }

    latest_score = solutions[0].get("score") or 0
    prev_score = solutions[1].get("score") or 0
    improvement = None
    if prev_score > 0:
        improvement = (latest_score - prev_score) / prev_score

    if mode == "exploration":
        requires_human = (improvement is not None) and (improvement < 0.05)
        return {
            "requires_human": requires_human,
            "converged": False,
            "done": False,
            "reason": (
                f"exploration: improvement {improvement:.2%} < 5% → requires_human={requires_human}"
                if improvement is not None
                else "exploration: no improvement data"
            ),
            "latest_score": latest_score,
            "improvement": improvement,
            "prev_score": prev_score,
        }

    elif mode == "optimization":
        if latest_score >= 90:
            return {
                "requires_human": False,
                "converged": False,
                "done": True,
                "reason": f"optimization: score {latest_score:.1f} >= 90 → done",
                "latest_score": latest_score,
                "improvement": improvement,
                "prev_score": prev_score,
            }
        if (improvement is not None) and (improvement < 0.01):
            return {
                "requires_human": False,
                "converged": True,
                "done": False,
                "reason": f"optimization: improvement {improvement:.2%} < 1% → converged",
                "latest_score": latest_score,
                "improvement": improvement,
                "prev_score": prev_score,
            }
        return {
            "requires_human": False,
            "converged": False,
            "done": False,
            "reason": f"optimization: improvement {improvement:.2%} >= 1%, score {latest_score:.1f} < 90 → continue",
            "latest_score": latest_score,
            "improvement": improvement,
            "prev_score": prev_score,
        }

    return {
        "requires_human": False,
        "converged": False,
        "done": False,
        "reason": f"mode={mode}: no convergence rule",
        "latest_score": latest_score,
        "improvement": improvement,
    }

def _adjust_constraints_for_goal(db: Session, goal_id: str) -> Dict[str, Any]:
    """根据上一轮结果自动调整约束"""
    prev_row = db.execute(
        text("""
            SELECT constraints FROM iteration_constraints
            WHERE goal_id = :gid ORDER BY round DESC LIMIT 1
        """),
        {"gid": goal_id}
    ).mappings().fetchone()

    constraints = {}
    if prev_row and prev_row.get("constraints"):
        raw = prev_row["constraints"]
        if isinstance(raw, str):
            try:
                constraints = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                constraints = {}
        elif isinstance(raw, dict):
            constraints = raw

    # 默认调整：所有数值约束收紧 5%
    adjusted = {}
    for key, value in constraints.items():
        if isinstance(value, (int, float)) and value > 0:
            adjusted[key] = round(value * 0.95, 2)
        else:
            adjusted[key] = value

    return adjusted