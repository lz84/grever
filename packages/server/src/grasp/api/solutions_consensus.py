
import uuid
from datetime import datetime
# -*- coding: utf-8 -*-
import json as _json
from loguru import logger

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from typing import Dict, Any
from sqlalchemy.orm import Session
from reins.common.database import get_db
from models import GoalIteration, IterationConstraint

router = APIRouter()

def _parse_discussion_list(ai_discussion):
    """Parse ai_discussion JSON field"""
    import json
    if not ai_discussion:
        return []
    try:
        return json.loads(ai_discussion)
    except (json.JSONDecodeError, TypeError):
        return []

def _detect_consensus(discussion):
    """Detect consensus in discussion"""
    # MVP: 硬编码规则，检查最后3条消息是否包含共识关键词
    if not discussion:
        return False
    consensus_keywords = ["同意", "共识", "达成一致", "OK", "好的", "确认", "approved", "agreed"]
    recent = discussion[-3:] if len(discussion) >= 3 else discussion
    for msg in recent:
        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
        if any(kw in content for kw in consensus_keywords):
            return True
    return False

def _serialize(val):
    """Serialize value to JSON string"""
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return json.dumps(val, ensure_ascii=False)

def _extract_constraints_from_discussion(discussion, goal_id, db):
    """Extract constraint adjustments from discussion"""
    # MVP: 硬编码规则，从讨论中提取约束调整
    return {
        "has_adjustments": False,
        "full_constraints": None,
        "reason": "No adjustments detected",
        "extracted": [],
    }

def _apply_consensus(goal_id: str, iter_id: str, db: Session) -> Dict[str, Any]:
    """
    应用共识：提取约束 → 写入新约束记录 → 创建下一轮迭代。

    返回：
    {
        "consensus": true,
        "constraints_updated": {...},
        "next_iteration_id": "iter-xxx",
        "next_iteration_number": N,
        "extraction_detail": {...}
    }
    """
    # 1. 获取当前迭代的讨论历史
    iter_row = db.query(GoalIteration).filter(
        GoalIteration.id == iter_id,
        GoalIteration.goal_id == goal_id
    ).first()

    if not iter_row:
        raise HTTPException(status_code=404, detail="Iteration not found")

    discussion = _parse_discussion_list(iter_row.ai_discussion)

    # 2. 检测共识
    has_consensus = _detect_consensus(discussion)
    if not has_consensus:
        return {
            "consensus": False,
            "message": "未检测到共识关键词，讨论仍在进行中。",
            "last_human_message": next((m.get("content") for m in reversed(discussion) if m.get("role") == "human"), ""),
        }

    # 3. 提取约束调整
    extraction = _extract_constraints_from_discussion(discussion, goal_id, db)

    # 4. 写入 iteration_constraints 表（新轮次）
    constraints_updated = {}
    if extraction["has_adjustments"]:
        # 获取当前最大 round
        from sqlalchemy import func
        prev_max = db.query(func.coalesce(func.max(IterationConstraint.round), 0)).filter(
            IterationConstraint.goal_id == goal_id
        ).scalar()
        new_round = (prev_max or 0) + 1

        constraint_id = f"ic-{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()

        new_constraint = IterationConstraint(
            id=constraint_id,
            goal_id=goal_id,
            round=new_round,
            constraints=_serialize(extraction["full_constraints"]),
            reason=extraction["reason"],
            created_by="consensus",
            created_at=now
        )
        db.add(new_constraint)
        constraints_updated = extraction["full_constraints"]
        db.commit()

        logger.info(f"[consensus] Goal {goal_id}: created constraint round {new_round}, id={constraint_id}")

    # 5. 创建下一轮 goal_iterations 记录
    from sqlalchemy import func
    max_iter = db.query(func.coalesce(func.max(GoalIteration.iteration_number), 0)).filter(
        GoalIteration.goal_id == goal_id
    ).scalar()
    next_number = (max_iter or 0) + 1

    next_iter_id = f"iter-{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow()

    next_iter = GoalIteration(
        id=next_iter_id,
        goal_id=goal_id,
        iteration_number=next_number,
        status="planned",
        created_at=now,
        updated_at=now
    )
    db.add(next_iter)
    db.commit()

    logger.info(f"[consensus] Goal {goal_id}: created next iteration {next_iter_id}, number={next_number}")

    return {
        "consensus": True,
        "constraints_updated": constraints_updated,
        "next_iteration_id": next_iter_id,
        "next_iteration_number": next_number,
        "extraction_detail": extraction["extracted"],
    }

# ============ 共识检测端点 ============

@router.post("/goals/{goal_id}/iterations/{iter_id}/consensus")

def trigger_consensus(goal_id: str, iter_id: str, db: Session = Depends(get_db)):
    """
    手动触发共识检测。

    解析讨论历史，提取约束调整，创建新约束记录和下一轮迭代。

    返回：
    {
        "consensus": true,
        "constraints_updated": {...},
        "next_iteration_id": "iter-xxx",
        "next_iteration_number": N,
        "extraction_detail": {...}
    }
    """
    result = _apply_consensus(goal_id, iter_id, db)
    return result

