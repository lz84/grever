from sqlalchemy import text
from datetime import datetime
# -*- coding: utf-8 -*-
import json
from fastapi import APIRouter, Depends, Query, status, Body, HTTPException
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from reins.common.database import get_db
from grasp.api.solutions_shared import CreateSolutionRequest, UpdateSolutionRequest
from grasp.api.solutions_helpers import _create_solution, _serialize, _row_to_solution, compare_solutions

router = APIRouter()

@router.post("/solutions", status_code=status.HTTP_201_CREATED)
def create_solution(req: CreateSolutionRequest, db: Session = Depends(get_db)):
    """创建方案（自动去重：同一 goal_id + round + parameters 不重复创建）"""
    # 去重检查：同目标、同轮次、同参数 → 返回已有方案，避免重复
    if req.goal_id and req.round is not None and req.parameters:
        params_hash = _serialize(req.parameters)
        existing = db.execute(
            text("""
                SELECT id FROM solutions
                WHERE goal_id = :gid AND round = :rnd AND parameters = :params
                LIMIT 1
            """),
            {"gid": req.goal_id, "rnd": req.round, "params": params_hash}
        ).fetchone()
        if existing:
            # 已存在，去重返回
            row = db.execute(text("SELECT * FROM solutions WHERE id = :id"), {"id": existing[0]}).mappings().fetchone()
            return _row_to_solution(row)

    sol = _create_solution(
        db=db,
        goal_id=req.goal_id,
        round_num=req.round,
        name=req.name or f"方案-{req.round}-新建",
        parameters=req.parameters,
        dimensions=req.dimensions,
        score=req.score,
        project_ids=req.project_ids,
        task_ids=req.task_ids,
        constraints=req.constraints,
    )
    return sol

@router.get("/solutions")

def list_solutions(
    goal_id: Optional[str] = Query(None, description="按目标ID过滤"),
    round_num: Optional[int] = Query(None, alias="round", description="按轮次过滤"),
    db: Session = Depends(get_db)
):
    """查询某目标下所有方案（支持 ?round=N 过滤）"""
    if not goal_id:
        return {"solutions": [], "total": 0}

    query = "SELECT * FROM solutions WHERE goal_id = :gid"
    params: Dict[str, Any] = {"gid": goal_id}

    if round_num is not None:
        query += " AND round = :r"
        params["r"] = round_num

    query += " ORDER BY round ASC, created_at ASC"

    rows = db.execute(text(query), params).mappings().fetchall()
    solutions = [_row_to_solution(r) for r in rows]

    return {"solutions": solutions, "total": len(solutions)}

# ============ 方案比较（静态路径，必须在 /solutions/{id} 之前） ============

@router.post("/solutions/compare")

def run_compare_solutions(
    goal_id: str = Body(..., embed=True, description="目标ID"),
    db: Session = Depends(get_db)
):
    """触发多维度加权评分计算，更新 solutions.score / status / is_optimal"""
    return compare_solutions(goal_id, db)

@router.get("/solutions/compare")

def get_compare_solutions(
    goal_id: str = Query(..., description="目标ID"),
    db: Session = Depends(get_db)
):
    """获取方案比较结果"""
    rows = db.execute(
        text("""
            SELECT * FROM solutions WHERE goal_id = :gid
            ORDER BY round ASC, score DESC
        """),
        {"gid": goal_id}
    ).mappings().fetchall()

    solutions = [_row_to_solution(r) for r in rows]

    # 找出最优方案
    optimal = None
    best_score = None
    for s in solutions:
        if s.get("is_optimal"):
            optimal = s
            break
        if s.get("score") is not None:
            if best_score is None or s["score"] > best_score:
                best_score = s["score"]
                optimal = s

    return {
        "goal_id": goal_id,
        "total_solutions": len(solutions),
        "solutions": solutions,
        "best_score": best_score,
        "optimal_solution": optimal,
    }

@router.get("/solutions/compare/multi")

def compare_solutions_multi(
    goal_id: str = Query(..., description="目标ID"),
    db: Session = Depends(get_db)
):
    """返回所有方案多维度数据"""
    rows = db.execute(
        text("""
            SELECT * FROM solutions WHERE goal_id = :gid
            ORDER BY round ASC, score DESC
        """),
        {"gid": goal_id}
    ).mappings().fetchall()

    # 收集所有维度
    all_dimensions = set()
    solutions_data = []

    for r in rows:
        dims = _parse_json_field(r.get("dimensions"))
        params = _parse_json_field(r.get("parameters"))

        if dims and isinstance(dims, dict):
            all_dimensions.update(dims.keys())

        solutions_data.append({
            "id": r.get("id"),
            "name": r.get("name"),
            "round": r.get("round"),
            "parameters": params or {},
            "status": r.get("status"),
            "score": r.get("score"),
            "is_optimal": bool(r.get("is_optimal", 0)),
            "dimensions": dims or {},
        })

    return {
        "goal_id": goal_id,
        "dimensions": sorted(list(all_dimensions)),
        "solutions": solutions_data,
    }

# ============ 收敛趋势 ============

@router.get("/solutions/trend")

def solution_trend(
    goal_id: str = Query(..., description="目标ID"),
    db: Session = Depends(get_db)
):
    """返回收敛趋势数据"""
    rows = db.execute(
        text("""
            SELECT round, dimensions, score, created_at
            FROM solutions WHERE goal_id = :gid
            ORDER BY round ASC, created_at ASC
        """),
        {"gid": goal_id}
    ).mappings().fetchall()

    rounds = []
    metrics: Dict[str, List] = {}
    scores = []

    for r in rows:
        rnd = r.get("round")
        if rnd not in rounds:
            rounds.append(rnd)
            scores.append(r.get("score"))

        dims = _parse_json_field(r.get("dimensions"))
        if dims and isinstance(dims, dict):
            for key, val in dims.items():
                if key not in metrics:
                    metrics[key] = []
                if len(metrics[key]) < len(rounds):
                    metrics[key].append(val)

    return {
        "goal_id": goal_id,
        "rounds": rounds,
        "metrics": metrics,
        "scores": scores,
    }

# ============ Solutions CRUD — Dynamic {id} paths (after static paths) ============

@router.get("/solutions/{solution_id}")

def get_solution(solution_id: str, db: Session = Depends(get_db)):
    """方案详情"""
    row = db.execute(
        text("SELECT * FROM solutions WHERE id = :id"),
        {"id": solution_id}
    ).mappings().fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Solution not found")

    return _row_to_solution(row)

@router.put("/solutions/{solution_id}")

def update_solution(solution_id: str, req: UpdateSolutionRequest, db: Session = Depends(get_db)):
    """更新方案（status, is_optimal, score 等）"""
    row = db.execute(
        text("SELECT * FROM solutions WHERE id = :id"),
        {"id": solution_id}
    ).mappings().fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Solution not found")

    updates = {}
    if req.status is not None:
        updates["status"] = req.status
    if req.is_optimal is not None:
        updates["is_optimal"] = 1 if req.is_optimal else 0
    if req.score is not None:
        updates["score"] = req.score
    if req.name is not None:
        updates["name"] = req.name
    if req.parameters is not None:
        updates["parameters"] = _serialize(req.parameters)
    if req.dimensions is not None:
        updates["dimensions"] = _serialize(req.dimensions)
    if req.project_ids is not None:
        updates["project_ids"] = _serialize(req.project_ids)
    if req.task_ids is not None:
        updates["task_ids"] = _serialize(req.task_ids)
    if req.constraints is not None:
        updates["constraints"] = _serialize(req.constraints)

    if updates:
        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        db.execute(
            text(f"UPDATE solutions SET {set_clause} WHERE id = :id"),
            {**updates, "id": solution_id}
        )
        db.commit()

    row = db.execute(
        text("SELECT * FROM solutions WHERE id = :id"),
        {"id": solution_id}
    ).mappings().fetchone()

    return _row_to_solution(row)

@router.delete("/solutions/{solution_id}", status_code=status.HTTP_204_NO_CONTENT)

def delete_solution(solution_id: str, db: Session = Depends(get_db)):
    """删除方案"""
    row = db.execute(
        text("SELECT id FROM solutions WHERE id = :id"),
        {"id": solution_id}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Solution not found")

    db.execute(text("DELETE FROM solutions WHERE id = :id"), {"id": solution_id})
    db.commit()
    return

# ================================================================
# 迭代模式 API 端点（Sprint 77）
# ================================================================

# ============ Pydantic 请求模型 ============

