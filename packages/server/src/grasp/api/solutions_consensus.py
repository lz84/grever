from sqlalchemy import text
import uuid
from datetime import datetime
# -*- coding: utf-8 -*-
import json as _json
from loguru import logger

from fastapi import APIRouter, Depends, Query, status, Body
from typing import Dict, Any
from sqlalchemy.orm import Session
from reins.common.database import get_db

router = APIRouter()

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
    iter_row = db.execute(
        text("SELECT ai_discussion, iteration_number FROM goal_iterations WHERE id = :id AND goal_id = :gid"),
        {"id": iter_id, "gid": goal_id}
    ).mappings().fetchone()

    if not iter_row:
        raise HTTPException(status_code=404, detail="Iteration not found")

    discussion = _parse_discussion_list(iter_row.get("ai_discussion"))

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
        prev_round_row = db.execute(
            text("SELECT COALESCE(MAX(round), 0) as max_round FROM iteration_constraints WHERE goal_id = :gid"),
            {"gid": goal_id}
        ).mappings().fetchone()
        new_round = (prev_round_row["max_round"] if prev_round_row else 0) + 1

        constraint_id = f"ic-{uuid.uuid4().hex[:12]}"
        now_iso = datetime.utcnow().isoformat()

        db.execute(
            text("""
                INSERT INTO iteration_constraints
                    (id, goal_id, round, constraints, reason, created_by, created_at)
                VALUES
                    (:id, :goal_id, :round, :constraints, :reason, :created_by, :created_at)
            """),
            {
                "id": constraint_id,
                "goal_id": goal_id,
                "round": new_round,
                "constraints": _serialize(extraction["full_constraints"]) if extraction["full_constraints"] else None,
                "reason": extraction["reason"],
                "created_by": "consensus",
                "created_at": now_iso,
            }
        )
        constraints_updated = extraction["full_constraints"]
        db.commit()

        logger.info(f"[consensus] Goal {goal_id}: created constraint round {new_round}, id={constraint_id}")

    # 5. 创建下一轮 goal_iterations 记录
    max_iter_row = db.execute(
        text("SELECT COALESCE(MAX(iteration_number), 0) as max_num FROM goal_iterations WHERE goal_id = :gid"),
        {"gid": goal_id}
    ).mappings().fetchone()
    next_number = (max_iter_row["max_num"] if max_iter_row else 0) + 1

    next_iter_id = f"iter-{uuid.uuid4().hex[:12]}"
    now_iso = datetime.utcnow().isoformat()

    db.execute(
        text("""
            INSERT INTO goal_iterations
                (id, goal_id, iteration_number, status, created_at, updated_at)
            VALUES
                (:id, :goal_id, :iter_num, :status, :created_at, :updated_at)
        """),
        {
            "id": next_iter_id,
            "goal_id": goal_id,
            "iter_num": next_number,
            "status": "planned",
            "created_at": now_iso,
            "updated_at": now_iso,
        }
    )
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

