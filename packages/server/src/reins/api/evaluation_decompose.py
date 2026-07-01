# -*- coding: utf-8 -*-
"""Evaluation Decomposition API — E-1~E-4 评估分解端点

POST /api/v1/evaluation-decompose/start     → E-1: 启动分解
POST /api/v1/evaluation-decompose/e2        → E-2: 解析 Agent 响应
POST /api/v1/evaluation-decompose/e3        → E-3: 提交用户答案
POST /api/v1/evaluation-decompose/e4        → E-4: 获取最终结果
GET  /api/v1/evaluation-decompose/status    → 查询分解状态
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from reins.common.database import get_db


router = APIRouter(prefix="/evaluation-decompose", tags=["evaluation-decompose"])


# =============================================================================
# Request/Response Models
# =============================================================================

class E1StartRequest(BaseModel):
    goal_id: str
    goal_title: str
    goal_description: str
    coordinator_agent_id: Optional[str] = None
    decomposition_mode: str = "auto"


class E1StartResponse(BaseModel):
    planning_session_id: str
    goal_session_id: str
    message: str


class E2ParseRequest(BaseModel):
    planning_session_id: str
    agent_response: Dict[str, Any] = Field(
        description="Agent response with sufficient, decomposition, tier0_questions, message"
    )


class Tier0QuestionSchema(BaseModel):
    question_id: str
    question_text: str
    question_type: str
    options: Optional[List[str]] = None
    default_answer: Optional[str] = None
    category: str = "general"
    answered: bool = False
    answer: Optional[str] = None


class E2ParseResponse(BaseModel):
    readiness: str  # ready | not_ready | hybrid
    sufficient: bool
    projects: List[Dict[str, Any]]
    tier0_questions: List[Tier0QuestionSchema]
    agent_message: str
    requires_hitl: bool


class E3SubmitRequest(BaseModel):
    planning_session_id: str
    answers: Dict[str, str] = Field(
        description="Mapping of question_id to answer"
    )


class E3SubmitResponse(BaseModel):
    status: str
    message: str


class E4FinalRequest(BaseModel):
    planning_session_id: str
    agent_final_response: Optional[Dict[str, Any]] = None


class E4FinalResponse(BaseModel):
    readiness: str
    projects: List[Dict[str, Any]]
    assumptions: List[str]
    default_applied: bool
    agent_message: str


class StatusResponse(BaseModel):
    planning_session_id: Optional[str] = None
    goal_session_id: Optional[str] = None
    status: str
    readiness: Optional[str] = None
    tier0_questions_count: int = 0


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/start", response_model=E1StartResponse)
def e1_start_decomposition(
    req: E1StartRequest,
    db: Session = Depends(get_db),
):
    """
    E-1: 启动分解流程

    创建一个 planning_session 和 goal_session，返回 session IDs。
    """
    from services.decomposition_readiness import EvaluationDecompositionService

    service = EvaluationDecompositionService(db)
    try:
        planning_id, goal_id = service.e1_start_decomposition(
            goal_id=req.goal_id,
            goal_title=req.goal_title,
            goal_description=req.goal_description,
            coordinator_agent_id=req.coordinator_agent_id,
            decomposition_mode=req.decomposition_mode,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 更新 goal 的分解状态
    service.update_goal_decomposition_status(
        goal_id=req.goal_id,
        status="in_progress",
        coordinator_agent_id=req.coordinator_agent_id,
    )

    return E1StartResponse(
        planning_session_id=planning_id,
        goal_session_id=goal_id,
        message=f"Decomposition started for goal {req.goal_id}",
    )


@router.post("/e2", response_model=E2ParseResponse)
def e2_parse_agent_response(
    req: E2ParseRequest,
    db: Session = Depends(get_db),
):
    """
    E-2: 解析 Coordinator Agent 的响应

    判断是否充分分解，返回 Tier 0 问题列表（如果需要 HITL）。
    """
    from services.decomposition_readiness import EvaluationDecompositionService

    service = EvaluationDecompositionService(db)
    try:
        result = service.e2_parse_agent_response(
            planning_session_id=req.planning_session_id,
            agent_response=req.agent_response,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return E2ParseResponse(
        readiness=result.readiness.value,
        sufficient=result.readiness.value == "ready",
        projects=result.projects,
        tier0_questions=[
            Tier0QuestionSchema(
                question_id=q.question_id,
                question_text=q.question_text,
                question_type=q.question_type,
                options=q.options,
                default_answer=q.default_answer,
                category=q.category,
                answered=q.answered,
                answer=q.answer,
            ) for q in result.tier0_questions
        ],
        agent_message=result.agent_message,
        requires_hitl=result.readiness.value == "not_ready",
    )


@router.post("/e3", response_model=E3SubmitResponse)
def e3_submit_answers(
    req: E3SubmitRequest,
    db: Session = Depends(get_db),
):
    """
    E-3: 用户提交 HITL 问题答案

    答案会被追加到 planning_session 的 discussion_log 中，
    之后 Grever 将答案发送给 Agent 进行下一轮分解。
    """
    from services.decomposition_readiness import EvaluationDecompositionService

    service = EvaluationDecompositionService(db)
    try:
        status = service.e3_submit_user_answers(
            planning_session_id=req.planning_session_id,
            answers=req.answers,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return E3SubmitResponse(
        status=status,
        message=f"Submitted {len(req.answers)} answers",
    )


@router.post("/e4", response_model=E4FinalResponse)
def e4_get_final_result(
    req: E4FinalRequest,
    db: Session = Depends(get_db),
):
    """
    E-4: 获取最终分解结果

    如果 Agent 最终响应仍不充分，使用默认分解提取逻辑。
    """
    from services.decomposition_readiness import EvaluationDecompositionService

    service = EvaluationDecompositionService(db)
    try:
        result = service.e4_get_final_result(
            planning_session_id=req.planning_session_id,
            agent_final_response=req.agent_final_response,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # 如果使用了默认分解，标记 goal
    if result.default_applied:
        planning = service.get_planning_session(req.planning_session_id)
        if planning:
            service.mark_default_decomposition_used(planning.goal_id)

    return E4FinalResponse(
        readiness=result.readiness.value,
        projects=result.projects,
        assumptions=result.assumptions,
        default_applied=result.default_applied,
        agent_message=result.agent_message,
    )


@router.get("/status/{planning_session_id}", response_model=StatusResponse)
def get_decomposition_status(
    planning_session_id: str,
    db: Session = Depends(get_db),
):
    """
    查询分解状态

    返回 planning_session 和 goal_session 的当前状态。
    """
    import json
    from services.decomposition_readiness import EvaluationDecompositionService
    from models.goal_session import GoalSession

    service = EvaluationDecompositionService(db)
    planning = service.get_planning_session(planning_session_id)

    if not planning:
        raise HTTPException(status_code=404, detail="Planning session not found")

    # 解析 discussion_log 中的 tier0 问题数量
    tier0_count = 0
    readiness = None
    try:
        log = planning.discussion_log
        if log:
            parsed = json.loads(log)
            for entry in parsed:
                if "tier0_questions" in entry:
                    tier0_count = len(entry.get("tier0_questions", []))
                if "role" in entry and entry.get("role") == "agent":
                    # 从 agent 消息中推断 readiness
                    content = entry.get("content", "")
                    if "sufficient" in content.lower() or "confirmed_plan" in content:
                        readiness = "ready"
                    elif tier0_count > 0:
                        readiness = "not_ready"
    except Exception:
        pass

    # 查找关联的 goal_session
    goal_session_id = None
    try:
        goal_session = db.query(GoalSession).filter(
            GoalSession.goal_id == planning.goal_id
        ).first()
        if goal_session:
            goal_session_id = goal_session.id
    except Exception:
        pass

    return StatusResponse(
        planning_session_id=planning.id,
        goal_session_id=goal_session_id,
        status=planning.status,
        readiness=readiness,
        tier0_questions_count=tier0_count,
    )


class Tier0QuestionsResponse(BaseModel):
    planning_session_id: str
    questions: List[Dict[str, Any]]
    agent_message: str
    readiness: str  # ready | not_ready | hybrid


@router.get("/questions/{planning_session_id}", response_model=Tier0QuestionsResponse)
def get_tier0_questions(
    planning_session_id: str,
    db: Session = Depends(get_db),
):
    """
    获取 Tier 0 问题列表

    从 planning_session.discussion_log 中解析出 Tier 0 问题。
    E-2 返回 insufficient 时，问题会存在 discussion_log 中。
    前端 HITL 页面调用此接口获取问题列表。
    """
    import json
    from services.decomposition_readiness import EvaluationDecompositionService

    service = EvaluationDecompositionService(db)
    planning = service.get_planning_session(planning_session_id)

    if not planning:
        raise HTTPException(status_code=404, detail="Planning session not found")

    # 解析 discussion_log 中的 Tier 0 问题
    questions: List[Dict[str, Any]] = []
    agent_message = ""
    readiness = "unknown"

    try:
        log = planning.discussion_log
        if log:
            parsed = json.loads(log)
            for entry in parsed:
                if "tier0_questions" in entry:
                    questions = entry.get("tier0_questions", [])
                if "role" in entry and entry.get("role") == "agent":
                    agent_message = entry.get("content", "")
                    # 判断 readiness
                    if planning.status == "pending_review":
                        readiness = "ready"
                    elif planning.status == "drafting":
                        readiness = "not_ready"
                    elif planning.status == "confirmed":
                        readiness = "hybrid"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse discussion log: {e}")

    return Tier0QuestionsResponse(
        planning_session_id=planning.id,
        questions=questions,
        agent_message=agent_message,
        readiness=readiness,
    )
