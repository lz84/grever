from models.solution import Solution
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
        existing = db.query(Solution.id).filter(
            Solution.goal_id == req.goal_id,
            Solution.round == req.round,
            Solution.parameters == params_hash
        ).first()
        if existing:
            # 已存在，去重返回
            solution = db.query(Solution).filter(Solution.id == existing[0]).first()
            return _row_to_solution({
                "id": solution.id, "goal_id": solution.goal_id, "round": solution.round,
                "name": solution.name, "status": solution.status,
                "parameters": solution.parameters, "dimensions": solution.dimensions,
                "score": solution.score, "is_optimal": solution.is_optimal,
                "project_ids": solution.project_ids, "task_ids": solution.task_ids,
                "constraints": solution.constraints,
                "created_at": solution.created_at, "updated_at": solution.updated_at,
            })

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

    query = db.query(Solution).filter(Solution.goal_id == goal_id)
    if round_num is not None:
        query = query.filter(Solution.round == round_num)
    query = query.order_by(Solution.round.asc(), Solution.created_at.asc())

    solutions = [_row_to_solution({
        "id": s.id, "goal_id": s.goal_id, "round": s.round,
        "name": s.name, "status": s.status, "parameters": s.parameters,
        "dimensions": s.dimensions, "score": s.score, "is_optimal": s.is_optimal,
        "project_ids": s.project_ids, "task_ids": s.task_ids,
        "constraints": s.constraints,
        "created_at": s.created_at, "updated_at": s.updated_at,
    }) for s in query.all()]

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
    solutions = db.query(Solution).filter(Solution.goal_id == goal_id).order_by(
        Solution.round.asc(), Solution.score.desc()
    ).all()

    solutions_data = [_row_to_solution({
        "id": s.id, "goal_id": s.goal_id, "round": s.round,
        "name": s.name, "status": s.status, "parameters": s.parameters,
        "dimensions": s.dimensions, "score": s.score, "is_optimal": s.is_optimal,
        "project_ids": s.project_ids, "task_ids": s.task_ids,
        "constraints": s.constraints,
        "created_at": s.created_at, "updated_at": s.updated_at,
    }) for s in solutions]

    # 找出最优方案
    optimal = None
    best_score = None
    for s in solutions_data:
        if s.get("is_optimal"):
            optimal = s
            break
        if s.get("score") is not None:
            if best_score is None or s["score"] > best_score:
                best_score = s["score"]
                optimal = s

    return {
        "goal_id": goal_id,
        "total_solutions": len(solutions_data),
        "solutions": solutions_data,
        "best_score": best_score,
        "optimal_solution": optimal,
    }

@router.get("/solutions/compare/multi")
def compare_solutions_multi(
    goal_id: str = Query(..., description="目标ID"),
    db: Session = Depends(get_db)
):
    """返回所有方案多维度数据"""
    solutions = db.query(Solution).filter(Solution.goal_id == goal_id).order_by(
        Solution.round.asc(), Solution.score.desc()
    ).all()

    # 收集所有维度
    all_dimensions = set()
    solutions_data = []

    for s in solutions:
        dims = _parse_json_field(s.dimensions)
        params = _parse_json_field(s.parameters)

        if dims and isinstance(dims, dict):
            all_dimensions.update(dims.keys())

        solutions_data.append({
            "id": s.id,
            "name": s.name,
            "round": s.round,
            "parameters": params or {},
            "status": s.status,
            "score": s.score,
            "is_optimal": bool(s.is_optimal or 0),
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
    solutions = db.query(Solution.round, Solution.dimensions, Solution.score, Solution.created_at).filter(
        Solution.goal_id == goal_id
    ).order_by(Solution.round.asc(), Solution.created_at.asc()).all()

    rounds = []
    metrics: Dict[str, List] = {}
    scores = []

    for s in solutions:
        rnd = s.round
        if rnd not in rounds:
            rounds.append(rnd)
            scores.append(s.score)

        dims = _parse_json_field(s.dimensions)
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
    solution = db.query(Solution).filter(Solution.id == solution_id).first()
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    return _row_to_solution({
        "id": solution.id, "goal_id": solution.goal_id, "round": solution.round,
        "name": solution.name, "status": solution.status,
        "parameters": solution.parameters, "dimensions": solution.dimensions,
        "score": solution.score, "is_optimal": solution.is_optimal,
        "project_ids": solution.project_ids, "task_ids": solution.task_ids,
        "constraints": solution.constraints,
        "created_at": solution.created_at, "updated_at": solution.updated_at,
    })

@router.put("/solutions/{solution_id}")
def update_solution(solution_id: str, req: UpdateSolutionRequest, db: Session = Depends(get_db)):
    """更新方案（status, is_optimal, score 等）"""
    solution = db.query(Solution).filter(Solution.id == solution_id).first()
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    if req.status is not None:
        solution.status = req.status
    if req.is_optimal is not None:
        solution.is_optimal = 1 if req.is_optimal else 0
    if req.score is not None:
        solution.score = req.score
    if req.name is not None:
        solution.name = req.name
    if req.parameters is not None:
        solution.parameters = _serialize(req.parameters)
    if req.dimensions is not None:
        solution.dimensions = _serialize(req.dimensions)
    if req.project_ids is not None:
        solution.project_ids = _serialize(req.project_ids)
    if req.task_ids is not None:
        solution.task_ids = _serialize(req.task_ids)
    if req.constraints is not None:
        solution.constraints = _serialize(req.constraints)

    solution.updated_at = datetime.utcnow()
    db.commit()

    return _row_to_solution({
        "id": solution.id, "goal_id": solution.goal_id, "round": solution.round,
        "name": solution.name, "status": solution.status,
        "parameters": solution.parameters, "dimensions": solution.dimensions,
        "score": solution.score, "is_optimal": solution.is_optimal,
        "project_ids": solution.project_ids, "task_ids": solution.task_ids,
        "constraints": solution.constraints,
        "created_at": solution.created_at, "updated_at": solution.updated_at,
    })

@router.delete("/solutions/{solution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_solution(solution_id: str, db: Session = Depends(get_db)):
    """删除方案"""
    solution = db.query(Solution).filter(Solution.id == solution_id).first()
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    db.delete(solution)
    db.commit()
    return

def _parse_json_field(data):
    """解析 JSON 字段"""
    if data is None:
        return None
    if isinstance(data, str):
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None
    return data

# ================================================================
# 迭代模式 API 端点（Sprint 77）
# ================================================================

# ============ Pydantic 请求模型 ============

