# -*- coding: utf-8 -*-
"""Decomposition Router - Read-only GET endpoints"""
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from reins.common.database import get_db
from models.planning_session import PlanningSession

router = APIRouter(prefix="/api/v1/goals", tags=["decomposition-read"])

def evaluate_and_decompose(
    goal_id: str,
    req: EvaluateDecomposeRequest,
    db: Session = Depends(get_db),
):
    """
    E-1: 启动评估分解流程

    1. 获取或创建 planning_session + goal_session
    2. 调用 call_agent("E-1", context) 发送评估请求
    3. 解析返回：
       - sufficient → 直接返回分解结果
       - insufficient → 返回 Tier 0 问题列表（requires_hitl=True）
    """
    from services.decomposition_readiness import (
        EvaluationDecompositionService,
        DecompositionReadiness,
    )
    from services.ai_agent_service import call_agent

    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    service = EvaluationDecompositionService(db)

    # 获取或创建 planning_session
    planning = db.query(PlanningSession).filter(
        PlanningSession.goal_id == goal_id
    ).order_by(PlanningSession.created_at.desc()).first()

    if not planning:
        # E-1: 创建 sessions
        planning_id, goal_session_id = service.e1_start_decomposition(
            goal_id=goal_id,
            goal_title=goal.title or "",
            goal_description=goal.description or "",
            coordinator_agent_id=req.coordinator_agent_id,
            decomposition_mode=req.decomposition_mode,
        )
        planning = db.query(PlanningSession).filter(
            PlanningSession.id == planning_id
        ).first()

    # 更新 goal 分解状态
    service.update_goal_decomposition_status(
        goal_id=goal_id,
        status="in_progress",
        coordinator_agent_id=req.coordinator_agent_id,
    )

    # 构建 E-1 上下文
    context = _build_e1_context(goal, planning, db)

    # 调用 E-1 Agent（含 fallback: 无 session 时用裸 LLM）
    try:
        agent_result = call_agent("E-1", context)
    except RuntimeError as e:
        # 没有可用的 Coordinator Session，降级为直接 LLM 调用
        logger.warning(f"[evaluate-decompose] E-1 session unavailable, using LLM fallback: {e}")
        agent_result = _llm_fallback_decomposition(context, "E-1")
    except Exception as e:
        logger.error(f"[evaluate-decompose] E-1 call_agent failed: {e}")
        raise HTTPException(status_code=502, detail=f"E-1 Agent 调用失败: {e}")

    # 解析 E-1 返回（兼容 prompt 模板格式: assessment/projects/questions）
    # 也支持旧格式: sufficient/decomposition/tier0_questions
    assessment = agent_result.get("assessment")  # E-1/E-3 模板用 assessment
    sufficient_flag = agent_result.get("sufficient")  # 旧格式兼容
    if assessment is not None:
        sufficient = assessment == "sufficient"
    elif sufficient_flag is not None:
        sufficient = bool(sufficient_flag)
    else:
        sufficient = False

    # projects 在 E-1 模板中是根级字段（不在 decomposition 下）
    decomposition = agent_result.get("decomposition") or {}
    projects_raw = agent_result.get("projects") or decomposition.get("projects", []) or []

    # questions → tier0_questions 格式转换
    questions_raw = agent_result.get("questions") or []
    tier0_raw = agent_result.get("tier0_questions") or questions_raw

    message = agent_result.get("message", "") or agent_result.get("agent_message", "")

    tier0_questions: List[Tier0QuestionOut] = []
    for q in tier0_raw:
        tier0_questions.append(Tier0QuestionOut(
            question_id=q.get("question_id") or f"q-{uuid.uuid4().hex[:8]}",
            question_text=q.get("question_text", ""),
            question_type=q.get("question_type", "text"),
            options=q.get("options"),
            category=q.get("category", "general"),
        ))

    # 更新 planning_session
    if sufficient:
        planning.status = "pending_review"
        # E-1 模板 projects 在根级，需包装为 {projects: [...]} 格式
        confirmed_payload = decomposition if decomposition else {"projects": projects_raw}
        planning.confirmed_plan = json.dumps(confirmed_payload, ensure_ascii=False)
        planning.decision_rationale = message
        readiness = "ready"
        requires_hitl = False
    else:
        existing = json.loads(planning.discussion_log or "[]")
        existing.append({
            "role": "agent",
            "content": message,
            "timestamp": datetime.utcnow().isoformat(),
            "tier0_questions": [q.model_dump() for q in tier0_questions],
        })
        planning.discussion_log = json.dumps(existing, ensure_ascii=False)
        planning.status = "drafting"
        readiness = "not_ready"
        requires_hitl = True

    db.commit()

    return EvaluateDecomposeResponse(
        planning_session_id=planning.id,
        readiness=readiness,
        sufficient=sufficient,
        projects=projects_raw if sufficient else [],
        tier0_questions=tier0_questions,
        agent_message=message,
        requires_hitl=requires_hitl,
    )


# ============================================================================
# Endpoint 2: GET /pending-questions  (P-1 问题获取)
# ============================================================================

@router.get("/{goal_id}/pending-questions")


def submit_answers(
    goal_id: str,
    req: SubmitAnswersRequest,
    db: Session = Depends(get_db),
):
    """
    E-3: 用户提交 HITL 问题答案

    1. 将答案追加到 planning_session.discussion_log
    2. 调用 call_agent("E-3", context) 继续评估
    3. 返回更新后的状态
    """
    from services.ai_agent_service import call_agent
    from services.decomposition_readiness import EvaluationDecompositionService

    planning = db.query(PlanningSession).filter(
        PlanningSession.id == req.planning_session_id,
        PlanningSession.goal_id == goal_id,
    ).first()

    if not planning:
        raise HTTPException(status_code=404, detail="PlanningSession not found")

    goal = db.query(Goal).filter(Goal.id == goal_id).first()

    # 追加用户答案到 discussion_log
    existing = json.loads(planning.discussion_log or "[]")
    existing.append({
        "role": "user",
        "content": json.dumps(req.answers, ensure_ascii=False),
        "timestamp": datetime.utcnow().isoformat(),
        "type": "hitl_answers",
    })
    planning.discussion_log = json.dumps(existing, ensure_ascii=False)
    db.commit()

    # 构建 E-3 上下文
    # E-3 prompt 期望: {goal_title, goal_description, previous_questions, user_answers}
    previous_questions = _extract_previous_questions(existing)
    context = {
        "goal_id": goal_id,
        "goal_title": goal.title or "" if goal else "",
        "goal_description": goal.description or "" if goal else "",
        "user_answers": json.dumps(req.answers, ensure_ascii=False),
        "previous_questions": json.dumps(previous_questions, ensure_ascii=False),
    }

    # 调用 E-3 Agent（含 fallback）
    try:
        agent_result = call_agent("E-3", context)
    except RuntimeError as e:
        logger.warning(f"[submit-answers] E-3 session unavailable, using LLM fallback: {e}")
        agent_result = _llm_fallback_decomposition(context, "E-3")
    except Exception as e:
        logger.error(f"[submit-answers] E-3 call_agent failed: {e}")
        raise HTTPException(status_code=502, detail=f"E-3 Agent 调用失败: {e}")

    # 解析 E-3 返回（兼容 assessment/sufficient 两种格式）
    assessment = agent_result.get("assessment")
    sufficient_flag = agent_result.get("sufficient")
    if assessment is not None:
        sufficient = assessment == "sufficient"
    elif sufficient_flag is not None:
        sufficient = bool(sufficient_flag)
    else:
        sufficient = False

    decomposition = agent_result.get("decomposition") or {}
    projects_raw = agent_result.get("projects") or decomposition.get("projects", []) or []
    message = agent_result.get("message", "") or agent_result.get("agent_message", "")

    if sufficient:
        planning.status = "pending_review"
        confirmed_payload = decomposition if decomposition else {"projects": projects_raw}
        planning.confirmed_plan = json.dumps(confirmed_payload, ensure_ascii=False)
        planning.decision_rationale = message
    else:
        planning.status = "e3_answered"
        # 如果仍有不足，追加新的 tier0 问题
        tier0_raw = agent_result.get("tier0_questions") or agent_result.get("questions") or []
        existing2 = json.loads(planning.discussion_log or "[]")
        existing2.append({
            "role": "agent",
            "content": message,
            "timestamp": datetime.utcnow().isoformat(),
            "tier0_questions": tier0_raw,
        })
        planning.discussion_log = json.dumps(existing2, ensure_ascii=False)

    db.commit()

    return SubmitAnswersResponse(
        status=planning.status,
        message=f"E-3 评估{'完成' if sufficient else '仍需补充'}: {message}",
        planning_session_id=planning.id,
    )


# ============================================================================
# Endpoint 4: GET /decomposition-preview  (预览)
# ============================================================================

@router.get("/{goal_id}/decomposition-preview")

