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

# ============ 工具函数 ============

