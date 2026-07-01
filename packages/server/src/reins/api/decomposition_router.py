# -*- coding: utf-8 -*-
"""Decomposition Router — Sprint 2 task-s2-3 E-1~E-4 评估分解路由

5 个 goal 级端点（挂载在 /api/v1/goals/{goal_id}/ 下）：

POST /evaluate-decompose         → evaluate_and_decompose  (E-1 启动)
GET  /pending-questions           → get_tier0_questions      (P-1 问题获取)
POST /submit-answers              → submit_answers           (E-3 提交答案)
GET  /decomposition-preview       → get_decomposition_preview (预览)
POST /confirm-decomposition      → confirm_decomposition    (D-1/D-2 写 DB)
"""
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from loguru import logger
from reins.api._decomp_helpers import _build_e1_context, _build_planning_context, _extract_previous_questions, _llm_fallback_decomposition, _trigger_task_assigner
from reins.api._decomp_read import router as decomp_read_router

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from reins.common.database import get_db
from models.goal import Goal
from models.planning_session import PlanningSession
from models.goal_session import GoalSession

router = APIRouter(prefix="/api/v1/goals", tags=["evaluation-decompose"])

router.include_router(decomp_read_router)


# ============================================================================
# Request / Response Models
# ============================================================================

class EvaluateDecomposeRequest(BaseModel):
    model_config = {"extra": "ignore"}
    coordinator_agent_id: Optional[str] = None
    decomposition_mode: str = "auto"
    force_reevaluate: bool = False


class Tier0QuestionOut(BaseModel):
    question_id: str
    question_text: str
    question_type: str
    options: Optional[List[str]] = None
    category: str = "general"
    answered: bool = False
    answer: Optional[str] = None


class EvaluateDecomposeResponse(BaseModel):
    planning_session_id: str
    readiness: str  # ready | not_ready | hybrid
    sufficient: bool
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    tier0_questions: List[Tier0QuestionOut] = Field(default_factory=list)
    agent_message: str = ""
    requires_hitl: bool = False


class SubmitAnswersRequest(BaseModel):
    model_config = {"extra": "ignore"}
    planning_session_id: str
    answers: Dict[str, str] = Field(
        description="Mapping of question_id → answer text"
    )


class SubmitAnswersResponse(BaseModel):
    status: str
    message: str
    planning_session_id: str


class DecompositionPreviewResponse(BaseModel):
    planning_session_id: Optional[str] = None
    status: str
    confirmed_plan: Optional[Dict[str, Any]] = None
    draft_versions: List[Dict[str, Any]] = Field(default_factory=list)
    discussion_log: List[Dict[str, Any]] = Field(default_factory=list)


class ConfirmDecompositionRequest(BaseModel):
    model_config = {"extra": "ignore"}
    planning_session_id: str
    projects_override: Optional[List[Dict[str, Any]]] = None


class ConfirmDecompositionResponse(BaseModel):
    success: bool
    goal_id: str
    projects_created: int = 0
    tasks_created: int = 0
    planning_session_id: str
    message: str


# ============================================================================
# Helper: build E-1 context for call_agent
# ============================================================================

@router.post("/{goal_id}/submit-answers", response_model=SubmitAnswersResponse)
@router.post("/{goal_id}/confirm-decomposition", response_model=ConfirmDecompositionResponse)
def confirm_decomposition(
    goal_id: str,
    req: ConfirmDecompositionRequest,
    db: Session = Depends(get_db),
):
    """
    D-2: 确认分解 + 写 DB + 触发 TaskAssigner

    1. 从 planning_session.confirmed_plan 获取分解产物
       （或使用 projects_override）
    2. 写入 projects + tasks 表
    3. 触发 TaskAssigner.assign_pending_tasks()
    4. 更新 goal.decomposition_status = "confirmed"
    """
    import uuid as uuid_lib

    from models.project import Project
    from models.task import Task
    from services.decomposition_readiness import EvaluationDecompositionService

    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    planning = db.query(PlanningSession).filter(
        PlanningSession.id == req.planning_session_id,
        PlanningSession.goal_id == goal_id,
    ).first()

    if not planning:
        raise HTTPException(status_code=404, detail="PlanningSession not found")

    # 获取分解产物
    decomposition = req.projects_override
    if not decomposition and planning.confirmed_plan:
        try:
            decomposition = json.loads(planning.confirmed_plan)
        except (json.JSONDecodeError, TypeError):
            decomposition = planning.confirmed_plan

    if not decomposition:
        raise HTTPException(
            status_code=400,
            detail="No decomposition plan found. Please evaluate first.",
        )

    projects_data = decomposition.get("projects", []) if isinstance(decomposition, dict) else decomposition

    if not projects_data:
        raise HTTPException(status_code=400, detail="Decomposition plan has no projects")

    # 写入 DB
    created_projects = 0
    created_tasks = 0

    for proj_data in projects_data:
        proj_name = proj_data.get("name", f"Project-{created_projects + 1}")
        priority_str = proj_data.get("priority", "medium")
        if priority_str not in ("high", "medium", "low"):
            priority_str = "medium"

        project = Project(
            id=f"project-{uuid_lib.uuid4().hex[:12]}",
            name=proj_name,
            description=proj_data.get("description", ""),
            priority=priority_str,
            goal_id=goal_id,
            status="active",
        )
        db.add(project)
        db.flush()

        # 写入 tasks
        tasks_data = proj_data.get("tasks", [])
        for task_data in tasks_data:
            task_priority = task_data.get("priority", "medium")
            if task_priority not in ("high", "medium", "low"):
                task_priority = "medium"

            task = Task(
                id=f"task-{uuid_lib.uuid4().hex[:12]}",
                project_id=project.id,
                title=task_data.get("title", "Untitled Task"),
                description=task_data.get("description", ""),
                status="pending",
                priority=task_priority,
                acceptance_criteria=task_data.get("acceptance_criteria"),
                capability_tags=json.dumps(task_data.get("capability_tags", []))
                    if task_data.get("capability_tags")
                    else None,
            )
            db.add(task)
            created_tasks += 1

        created_projects += 1

    # 更新 planning_session
    planning.status = "confirmed"
    planning.confirmed_at = datetime.utcnow().isoformat()

    # 更新 goal 状态（通过状态机）
    from reins.scheduler.statemachine import GoalStateMachine
    fsm = GoalStateMachine(db, goal_id)
    fsm.transition("planned", reason="分解完成", extra={"decomposition_status": "confirmed", "updated_at": int(datetime.utcnow().timestamp())})

    db.commit()

    # 触发 TaskAssigner（异步，不阻塞响应）
    _trigger_task_assigner(goal_id)

    logger.info(
        f"[confirm-decomposition] Wrote {created_projects} projects, "
        f"{created_tasks} tasks for goal {goal_id}"
    )

    return ConfirmDecompositionResponse(
        success=True,
        goal_id=goal_id,
        projects_created=created_projects,
        tasks_created=created_tasks,
        planning_session_id=planning.id,
        message=f"成功创建 {created_projects} 个项目，{created_tasks} 个任务",
    )
