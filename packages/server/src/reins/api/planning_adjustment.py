# -*- coding: utf-8 -*-
"""
规划调整模块 — Sprint 6 task-s6-4
提供 PA-1/PA-2 模板管理、trigger_planning_adjustment()、check_if_adjustment_needed()
及 FastAPI 路由：POST /api/v1/goals/{id}/planning-adjustment
               GET  /api/v1/goals/{id}/planning-adjustment/status
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.goal import Goal
from models.planning_session import PlanningSession
from models.verification_report import VerificationReport
from reins.common.database import get_db
from reins.api._planning_adjustment_templates import (
    PA1_TEMPLATE, PA2_TEMPLATE, PA1_CONTEXT_SCHEMA, PA1_OUTPUT_SCHEMA,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["goals"])


class TriggerAdjustmentRequest(BaseModel):
    reason: str
    verification_report_id: Optional[str] = None


class AdjustmentStatusResponse(BaseModel):
    goal_id: str
    has_active_adjustment: bool
    last_adjustment_at: Optional[str] = None
    last_adjustment_reason: Optional[str] = None
    adjustment_needed: bool = False
    needs_review: bool = False


def seed_pa_templates() -> Dict[str, Any]:
    """将 PA-1/PA-2 模板写入 prompt_library 表。"""
    try:
        from services.ai_agent_service import update_prompt_template
        r1 = update_prompt_template("PA-1", PA1_TEMPLATE,
            context_schema=PA1_CONTEXT_SCHEMA, output_schema=PA1_OUTPUT_SCHEMA,
            category="planning", description="规划调整请求 — Grever → Coordinator Agent")
        r2 = update_prompt_template("PA-2", PA2_TEMPLATE,
            context_schema={}, output_schema={},
            category="planning", description="规划调整方案 — Coordinator Agent → Grever")
        logger.info(f"[seed_pa_templates] PA-1 v{r1.get('version')}, PA-2 v{r2.get('version')} seeded")
        return {"PA-1": r1.get("version"), "PA-2": r2.get("version")}
    except Exception as e:
        logger.error(f"[seed_pa_templates] Failed: {e}")
        return {"error": str(e)}


def check_if_adjustment_needed(vr: VerificationReport) -> bool:
    """判断 VerificationReport 是否触发规划调整：gaps>3 / high severity / 同类重复≥2"""
    raw = vr.gaps
    if not raw:
        return False
    gaps: List[Dict[str, str]] = json.loads(raw) if isinstance(raw, str) else (raw if isinstance(raw, list) else [])
    if len(gaps) > 3:
        return True
    for g in gaps:
        if g.get("severity", "").lower() == "high":
            return True
    seen: Dict[str, int] = {}
    for g in gaps:
        k = g.get("gap", "")[:30]
        if seen.get(k, 0) >= 1:
            return True
        seen[k] = seen.get(k, 0) + 1
    return False


def _parse_confirmed_plan(ps: Optional[PlanningSession]) -> str:
    cp = ps.confirmed_plan if ps else None
    if not cp:
        return "{}"
    return cp if isinstance(cp, str) else json.dumps(cp, ensure_ascii=False)


async def trigger_planning_adjustment(
    goal_id: str,
    reason: str,
    db: Session,
    verification_report_id: Optional[str] = None,
) -> Dict[str, Any]:
    """触发规划调整：收集上下文 → call_agent(PA-1) → 更新 planning_session"""
    goal: Optional[Goal] = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise ValueError(f"Goal not found: {goal_id}")

    ps: Optional[PlanningSession] = (
        db.query(PlanningSession)
        .filter(PlanningSession.goal_id == goal_id)
        .order_by(PlanningSession.created_at.desc()).first()
    )
    confirmed_plan = _parse_confirmed_plan(ps)

    # Build feedback summary from verification report
    feedback_summary = reason
    vr: Optional[VerificationReport] = None
    if verification_report_id:
        vr = db.query(VerificationReport).filter(VerificationReport.id == verification_report_id).first()
        if vr:
            gaps_raw = vr.gaps
            gaps_str = json.dumps(json.loads(gaps_raw) if isinstance(gaps_raw, str) else (gaps_raw or []), ensure_ascii=False)
            feedback_summary = f"{reason}\n\n验证摘要：{vr.summary or '无'}\n缺口：{gaps_str}"

    # Build PA-1 context
    context = {
        "adjustment_reason": reason,
        "feedback_summary": feedback_summary,
        "context_md": goal.context_md or "（无上下文文档）",
        "confirmed_plan": confirmed_plan,
    }

    # Call Coordinator Agent
    try:
        from services.ai_agent_service import call_agent
        pa1_result = call_agent("PA-1", context, goal_id=goal_id)
        logger.info(f"[trigger_planning_adjustment] PA-1 result: {str(pa1_result)[:200]}")
    except Exception as e:
        logger.error(f"[trigger_planning_adjustment] PA-1 call failed: {e}")
        pa1_result = {"needs_adjustment": False, "rationale": f"Agent 调用失败：{e}"}

    needs_adj = pa1_result.get("needs_adjustment", False)
    resp_json = json.dumps(pa1_result, ensure_ascii=False)
    now_str = datetime.utcnow().isoformat()
    rationale = f"[{now_str}] {'需要调整' if needs_adj else '不需要调整'}：{pa1_result.get('rationale', 'N/A')}"

    if ps:
        log = json.loads(ps.discussion_log) if ps.discussion_log and isinstance(ps.discussion_log, str) else (ps.discussion_log or [])
        log.extend([
            {"role": "nexus", "content": f"规划调整请求（{now_str}）：{reason}", "timestamp": now_str},
            {"role": "coordinator", "content": resp_json, "timestamp": now_str},
        ])
        ps.discussion_log = json.dumps(log, ensure_ascii=False)
        ps.trigger_type = "execution_feedback"
        ps.status = "drafting" if needs_adj else ps.status
        ps.decision_rationale = rationale
        db.commit()
        ps_id = ps.id
    else:
        ps_id = f"ps-{goal_id.split('-')[-1][:12]}-{now_str[-8:].replace(':', '')}"
        new_ps = PlanningSession(
            id=ps_id, goal_id=goal_id, trigger_type="execution_feedback",
            input_type="text", input_content=reason,
            discussion_log=json.dumps([
                {"role": "nexus", "content": f"规划调整请求（{now_str}）", "timestamp": now_str},
                {"role": "coordinator", "content": resp_json, "timestamp": now_str},
            ], ensure_ascii=False),
            status="drafting" if needs_adj else "confirmed",
            confirmed_plan=None, decision_rationale=rationale, created_at=now_str,
        )
        db.add(new_ps)
        db.commit()
        logger.info(f"[trigger_planning_adjustment] Created planning_session {ps_id}")

    return {
        "goal_id": goal_id, "planning_session_id": ps_id,
        "needs_adjustment": needs_adj,
        "adjustment_type": pa1_result.get("adjustment_type"),
        "changes": pa1_result.get("changes", []),
        "rationale": pa1_result.get("rationale"),
        "trigger_reason": reason, "triggered_at": now_str,
        "status": "adjustment_triggered" if needs_adj else "no_adjustment_needed",
    }


@router.post("/{goal_id}/planning-adjustment")
async def post_planning_adjustment(goal_id: str, request: TriggerAdjustmentRequest, db: Session = Depends(get_db)):
    """POST /api/v1/goals/{id}/planning-adjustment"""
    try:
        return await trigger_planning_adjustment(goal_id, request.reason, db, request.verification_report_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[post_planning_adjustment] error: {e}")
        raise HTTPException(status_code=500, detail=f"规划调整失败：{e}")


@router.get("/{goal_id}/planning-adjustment/status", response_model=AdjustmentStatusResponse)
def get_adjustment_status(goal_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/goals/{id}/planning-adjustment/status"""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    ps: Optional[PlanningSession] = (
        db.query(PlanningSession)
        .filter(PlanningSession.goal_id == goal_id)
        .order_by(PlanningSession.created_at.desc()).first()
    )
    if not ps:
        return AdjustmentStatusResponse(goal_id=goal_id, has_active_adjustment=False,
            last_adjustment_at=None, last_adjustment_reason=None,
            adjustment_needed=False, needs_review=False)
    rationale = ps.decision_rationale or ""
    is_drafting = ps.status == "drafting"
    return AdjustmentStatusResponse(
        goal_id=goal_id, has_active_adjustment=is_drafting,
        last_adjustment_at=ps.created_at, last_adjustment_reason=rationale[:200],
        adjustment_needed="需要调整" in rationale,
        needs_review=is_drafting or "需要调整" in rationale,
    )
