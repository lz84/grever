# -*- coding: utf-8 -*-
"""
Solutions API — 方案库管理 + 迭代决策回路 + 对比趋势

路由顺序注意：静态路径必须在动态 {id} 路径之前注册，
否则 "compare" 会被当作 solution_id 匹配。

端点:
- POST   /api/v1/solutions                     创建方案
- GET    /api/v1/solutions?goal_id=xxx         查询某目标下所有方案
- GET    /api/v1/solutions/compare?goal_id=xxx  方案比较
- GET    /api/v1/solutions/compare/multi        多维度比较
- GET    /api/v1/solutions/trend?goal_id=xxx    收敛趋势
- GET    /api/v1/solutions/{id}                方案详情
- PUT    /api/v1/solutions/{id}                更新方案
- DELETE /api/v1/solutions/{id}                删除方案
- POST   /api/v1/goals/{id}/mode               切换模式
- POST   /api/v1/goals/{id}/start-iteration     启动迭代回路
- GET    /api/v1/goals/{id}/iteration-status    迭代状态
- POST   /api/v1/goals/{id}/iterate             触发下一轮迭代
- GET    /api/v1/goals/{id}/constraints         约束历史
- POST   /api/v1/goals/{goal_id}/iterations     创建迭代记录 (Sprint 77)
- GET    /api/v1/goals/{goal_id}/iterations     获取迭代历史 (Sprint 77)
- POST   /api/v1/goals/{goal_id}/iterations/{iter_id}/analysis  生成AI分析 (Sprint 77)
- POST   /api/v1/goals/{goal_id}/iterations/{iter_id}/discuss   发送讨论消息 (Sprint 77)
- POST   /api/v1/goals/{goal_id}/iterations/{iter_id}/consensus 手动触发共识检测 (Sprint 78)
"""

from loguru import logger

import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from sqlalchemy import text

from reins.common.database import get_db
from models.solution import Solution, SolutionStatus, SolutionCreate, SolutionUpdate
from models.iteration_constraint import IterationConstraint

router = APIRouter(prefix="/api/v1", tags=["solutions"])

# ============ Pydantic 请求模型 ============

class CreateSolutionRequest(BaseModel):
    goal_id: str
    round: int = 1
    name: Optional[str] = None
    parameters: Optional[Any] = None  # accepts dict or JSON string
    dimensions: Optional[Any] = None
    score: Optional[float] = None
    project_ids: Optional[Any] = None  # accepts list or JSON string
    task_ids: Optional[Any] = None
    constraints: Optional[Any] = None

class UpdateSolutionRequest(BaseModel):
    status: Optional[str] = None
    is_optimal: Optional[bool] = None
    score: Optional[float] = None
    name: Optional[str] = None
    parameters: Optional[Any] = None
    dimensions: Optional[Any] = None
    project_ids: Optional[Any] = None
    task_ids: Optional[Any] = None
    constraints: Optional[Any] = None

class SetGoalModeRequest(BaseModel):
    mode: str = Field(..., description="normal|exploration|optimization")
    optimization_target: Optional[str] = None
    convergence_threshold: Optional[float] = None
    max_rounds: Optional[int] = None

class StartIterationRequest(BaseModel):
    initial_constraints: Optional[Dict[str, Any]] = None

class IterateRequest(BaseModel):
    constraint_adjustments: Optional[Dict[str, Any]] = None


# ============ 迭代回路支撑函数 (供 goals_exploration_iteration.py 调用) ============

def auto_capture_solution(goal_id: str, db: Session) -> Optional[Dict[str, Any]]:
    """
    自动捕获当前最佳方案作为新轮次候选。
    返回创建的 Solution 记录 dict，或 None（无可捕获内容时）。
    """
    from models import Goal
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        return None

    from models import Solution
    from sqlalchemy import func
    max_round = db.query(func.max(Solution.round)).filter(
        Solution.goal_id == goal_id
    ).scalar() or 0

    if max_round == 0:
        solution_id = f"sol-{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()
        sol = Solution(
            id=solution_id,
            goal_id=goal_id,
            round=1,
            name="初始方案",
            parameters=goal.context_md or "{}",
            score=0.0,
            status="candidate",
            is_optimal=False,
            created_at=now,
        )
        db.add(sol)
        db.commit()
        return {"id": solution_id, "goal_id": goal_id, "round": 1, "name": "初始方案"}
    return None


def compare_solutions(goal_id: str, db: Session) -> Dict[str, Any]:
    """
    对比当前轮次所有方案，更新 is_optimal 标记。
    返回 {"updated": N} 表示更新的方案数量。
    """
    from models import Solution
    from sqlalchemy import func

    max_score = db.query(func.max(Solution.score)).filter(
        Solution.goal_id == goal_id
    ).scalar() or 0.0

    current_round = db.query(func.max(Solution.round)).filter(
        Solution.goal_id == goal_id
    ).scalar() or 1

    updated = 0
    if max_score > 0:
        db.query(Solution).filter(
            Solution.goal_id == goal_id,
            Solution.is_optimal == True,
        ).update({"is_optimal": False})
        rows = db.query(Solution).filter(
            Solution.goal_id == goal_id,
            Solution.round == current_round,
        ).all()
        for row in rows:
            if row.score == max_score:
                row.is_optimal = True
                updated += 1
        db.commit()
    return {"updated": updated}


def adjust_constraints_for_next_round(goal_id: str, db: Session) -> Dict[str, Any]:
    """
    根据当前收敛情况，生成下一轮约束调整建议。
    """
    from models import Solution, IterationConstraint
    from sqlalchemy import func

    current_round = db.query(func.max(Solution.round)).filter(
        Solution.goal_id == goal_id
    ).scalar() or 1

    last_constraints = db.query(IterationConstraint).filter(
        IterationConstraint.goal_id == goal_id,
        IterationConstraint.round == current_round,
    ).first()

    new_constraints = {}
    if last_constraints:
        try:
            old = json.loads(last_constraints.constraints) if isinstance(last_constraints.constraints, str) else (last_constraints.constraints or {})
        except Exception:
            old = {}
        new_constraints = dict(old)

    next_round = current_round + 1
    ic = IterationConstraint(
        id=f"ic-{uuid.uuid4().hex[:12]}",
        goal_id=goal_id,
        round=next_round,
        constraints=json.dumps(new_constraints, ensure_ascii=False),
        reason="自动调整约束",
        created_by="system",
        created_at=datetime.utcnow().isoformat(),
    )
    db.add(ic)
    db.commit()
    return {"new_constraints": new_constraints}


# ============ 工具函数 ============

