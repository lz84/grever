import uuid
from fastapi import HTTPException
# -*- coding: utf-8 -*-
import json
from loguru import logger

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import APIRouter, status, Query
from models import Solution
from grasp.api.solutions_convergence import check_convergence, _track_convergence_streak
router = APIRouter()
def _serialize(val):
    """将值序列化为 JSON 字符串"""
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return json.dumps(val, ensure_ascii=False)
def _parse_json_field(val):
    """解析 JSON 字段"""
    if val is None:
        return None
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    return val

def _row_to_solution(row) -> dict:
    """将数据库行转为方案字典（兼容 dict 或 ORM 对象）"""
    if row is None:
        return None
    # Support both dict (.get) and ORM object (getattr)
    def _get(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
    return {
        "id": _get(row, "id"),
        "goal_id": _get(row, "goal_id"),
        "round": _get(row, "round"),
        "name": _get(row, "name"),
        "status": _get(row, "status"),
        "parameters": _parse_json_field(_get(row, "parameters")),
        "dimensions": _parse_json_field(_get(row, "dimensions")),
        "score": _get(row, "score"),
        "is_optimal": bool(_get(row, "is_optimal", 0)),
        "project_ids": _parse_json_field(_get(row, "project_ids")),
        "task_ids": _parse_json_field(_get(row, "task_ids")),
        "constraints": _parse_json_field(_get(row, "constraints")),
        "created_at": _get(row, "created_at"),
        "updated_at": _get(row, "updated_at"),
    }
# ============ 收敛判断核心函数 ============
import statistics

def _create_solution(db: Session, goal_id: str, round_num: int, name: str,
                     score: float = None, project_ids: list = None,
                     task_ids: list = None, constraints: dict = None,
                     status: str = "compliant",
                     parameters=None, dimensions=None) -> dict:
    """创建方案并写入数据库"""
    sol_id = f"sol-{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow()

    new_solution = Solution(
        id=sol_id,
        goal_id=goal_id,
        round=round_num,
        name=name,
        status=status,
        parameters=_serialize(parameters),
        dimensions=_serialize(dimensions),
        score=score,
        is_optimal=False,
        project_ids=_serialize(project_ids),
        task_ids=_serialize(task_ids),
        constraints=_serialize(constraints),
        created_at=now,
        updated_at=now,
    )
    db.add(new_solution)
    db.commit()

    # Fetch the created solution via ORM
    row = db.query(Solution).filter(Solution.id == sol_id).first()

    return _row_to_solution(row)

# ============ 多维度加权评分引擎 ============

def compare_solutions(goal_id: str, db: Session) -> dict:
    """
    多方案多维度加权评分计算。

    评分公式（归一化到 0-100）：
      score = duration_score * 35% + cost_score * 35% + safety_score * 30%

    - duration（工期）：越低越好 → score = 100 - 归一化值
    - cost（成本）：越低越好 → score = 100 - 归一化值
    - safety/risk（安全系数）：越高越好 → score = 归一化值

    状态判定：
      score >= 80 → compliant（达标）
      60 <= score < 80 → non_compliant（不达标）
      score < 60 → rejected（否决）

    最优标记：score 最高的方案 is_optimal=1（同一 goal 下只有 1 个）
    """
    import re

    def _safe_float(val, default=None):
        if val is None:
            return default
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    def _extract_metric(params: dict, *keys) -> float | None:
        """从 parameters dict 中提取指标，尝试多个可能的 key 名称"""
        if not params:
            return None
        for key in keys:
            # 支持中文和英文 key
            val = params.get(key) or params.get(key.lower()) or params.get(key.upper())
            if val is not None:
                f = _safe_float(val)
                if f is not None:
                    return f
        return None

    def _normalize(value: float, min_val: float, max_val: float) -> float:
        """min-max 归一化到 [0, 100]"""
        if max_val <= min_val:
            return 50.0  # 只有一个值时给中间分
        return (value - min_val) / (max_val - min_val) * 100.0

    # 1. 获取该 goal 下所有方案
    rows = db.query(Solution).filter(
        Solution.goal_id == goal_id
    ).order_by(Solution.round.asc(), Solution.created_at.asc()).all()

    if not rows:
        return {"goal_id": goal_id, "message": "No solutions found", "updated": 0}

    # 2. 解析所有方案的 parameters，提取 duration / cost / safety
    solutions = []
    for row in rows:
        params = _parse_json_field(row.get("parameters")) or {}
        # 尝试多种 key 名称
        duration = (
            _extract_metric(params, "工期", "duration", "duration_hours", "工期_days", "days")
            or _extract_metric(params, "time", "time_hours", "hours")
        )
        cost = (
            _extract_metric(params, "成本", "cost", "cost_usd", "cost_usd")
            or _extract_metric(params, "price", "费用")
        )
        # safety/risk: risk=low→100, medium→50, high→0; 或者直接的 safety 数值
        safety = None
        risk_key = params.get("risk") or params.get("风险")
        if risk_key is not None:
            risk_lower = str(risk_key).lower()
            if risk_lower in ("low", "l", "低", "0"):
                safety = 100.0
            elif risk_lower in ("medium", "m", "中", "1"):
                safety = 50.0
            elif risk_lower in ("high", "h", "高", "2"):
                safety = 10.0
        if safety is None:
            safety = _extract_metric(params, "safety", "safety_score", "安全系数", "quality")
        if safety is None:
            safety = _extract_metric(params, "quality", "score")

        solutions.append({
            "id": row.get("id"),
            "row": dict(row),
            "params": params,
            "duration": duration,
            "cost": cost,
            "safety": safety,
        })

    # 3. 收集各维度范围（只对非 None 值计算）
    durations = [s["duration"] for s in solutions if s["duration"] is not None]
    costs = [s["cost"] for s in solutions if s["cost"] is not None]
    safeties = [s["safety"] for s in solutions if s["safety"] is not None]

    has_duration = len(durations) > 0
    has_cost = len(costs) > 0
    has_safety = len(safeties) > 0

    dur_min, dur_max = (min(durations), max(durations)) if has_duration else (0, 0)
    cost_min, cost_max = (min(costs), max(costs)) if has_cost else (0, 0)
    saf_min, saf_max = (min(safeties), max(safeties)) if has_safety else (0, 0)

    # 4. 计算每个方案的评分
    updated = 0
    for sol in solutions:
        dur_score = 100.0
        cost_score = 100.0
        saf_score = 100.0

        if sol["duration"] is not None and has_duration:
            norm = _normalize(sol["duration"], dur_min, dur_max)
            dur_score = 100.0 - norm  # 越低越好
        elif has_duration:
            dur_score = 50.0  # 无 duration 数据

        if sol["cost"] is not None and has_cost:
            norm = _normalize(sol["cost"], cost_min, cost_max)
            cost_score = 100.0 - norm  # 越低越好
        elif has_cost:
            cost_score = 50.0

        if sol["safety"] is not None and has_safety:
            saf_score = _normalize(sol["safety"], saf_min, saf_max)  # 越高越好
        elif has_safety:
            saf_score = 50.0

        # 权重：duration 35% + cost 35% + safety 30%
        total_weight = 0.0
        weighted = 0.0
        if has_duration:
            weighted += dur_score * 0.35
            total_weight += 0.35
        if has_cost:
            weighted += cost_score * 0.35
            total_weight += 0.35
        if has_safety:
            weighted += saf_score * 0.30
            total_weight += 0.30

        if total_weight > 0:
            score = weighted / total_weight
        else:
            score = 0.0

        # 状态判定
        if score >= 80:
            status_val = "compliant"
        elif score >= 60:
            status_val = "non_compliant"
        else:
            status_val = "rejected"

        # 更新 DB
        now_iso = datetime.utcnow().isoformat()
        db.query(Solution).filter(Solution.id == sol["id"]).update({
            "score": round(score, 2),
            "status": status_val,
            "updated_at": now_iso,
        })
        updated += 1

    # 5. 标记最优方案（score 最高者 is_optimal=1）
    db.query(Solution).filter(Solution.goal_id == goal_id).update({"is_optimal": False})
    best = db.query(Solution.id).filter(
        Solution.goal_id == goal_id,
        Solution.score.isnot(None)
    ).order_by(Solution.score.desc()).first()
    if best:
        db.query(Solution).filter(Solution.id == best.id).update({"is_optimal": True})

    db.commit()

    # 6. 返回结果
    result_rows = db.query(Solution).filter(
        Solution.goal_id == goal_id
    ).order_by(Solution.score.desc()).all()

    # 7. 收敛判断（每次评分后检查）
    converged, conv_reason = check_convergence(goal_id, db)
    streak = _track_convergence_streak(goal_id, converged, db)

    return {
        "goal_id": goal_id,
        "updated": updated,
        "solutions": [{
            "id": r.id,
            "name": r.name,
            "score": r.score,
            "status": r.status,
            "is_optimal": bool(r.is_optimal),
        } for r in result_rows],
        "converged": converged,
        "convergence_reason": conv_reason,
        "convergence_streak": streak,
        "auto_execute_triggered": streak >= 3 if converged else False,
    }

# ============ 约束自动调整引擎 ============

