from sqlalchemy import text
import json
import uuid
from datetime import datetime
# -*- coding: utf-8 -*-
from loguru import logger

from fastapi import APIRouter, Depends, Query, status, Body, HTTPException
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from reins.common.database import get_db
from grasp.api.solutions_consensus import _apply_consensus
from grasp.api.solutions_discussion import _generate_ai_reply
from grasp.api.solutions_iteration_helpers import _generate_ai_analysis, CreateIterationRequest, DiscussRequest

router = APIRouter()

def create_iteration(goal_id: str, req: CreateIterationRequest = Body(default=None), db: Session = Depends(get_db)):
    """
    创建迭代记录。
    自动生成 iteration_number = max + 1。
    返回: {"id": "iter-xxx", "iteration_number": 3, "status": "planned"}
    """
    # 验证 goal 存在
    goal_row = db.execute(
        text("SELECT id, title FROM goals WHERE id = :id"),
        {"id": goal_id}
    ).mappings().fetchone()
    if not goal_row:
        raise HTTPException(status_code=404, detail="Goal not found")

    # 计算下一个 iteration_number
    max_row = db.execute(
        text("SELECT COALESCE(MAX(iteration_number), 0) as max_num FROM goal_iterations WHERE goal_id = :gid"),
        {"gid": goal_id}
    ).mappings().fetchone()
    next_number = (max_row["max_num"] if max_row else 0) + 1

    # 创建迭代记录
    iter_id = f"iter-{uuid.uuid4().hex[:12]}"
    now_iso = datetime.utcnow().isoformat()

    db.execute(
        text("""
            INSERT INTO goal_iterations
                (id, goal_id, iteration_number, status, created_at, updated_at)
            VALUES
                (:id, :goal_id, :iter_num, :status, :created_at, :updated_at)
        """),
        {
            "id": iter_id,
            "goal_id": goal_id,
            "iter_num": next_number,
            "status": "planned",
            "created_at": now_iso,
            "updated_at": now_iso,
        }
    )
    db.commit()

    return {
        "id": iter_id,
        "iteration_number": next_number,
        "status": "planned",
        "goal_id": goal_id,
    }

@router.get("/goals/{goal_id}/iterations")

def list_iterations(
    goal_id: str,
    db: Session = Depends(get_db)
):
    """
    获取迭代历史。
    返回: [{"id": "iter-xxx", "iteration_number": 1, "solution_id": "...",
            "score": 0.82, "status": "completed", "ai_analysis": "...",
            "ai_discussion": [...], "created_at": "..."}, ...]
    """
    # 验证 goal 存在
    goal_row = db.execute(
        text("SELECT id FROM goals WHERE id = :id"),
        {"id": goal_id}
    ).fetchone()
    if not goal_row:
        raise HTTPException(status_code=404, detail="Goal not found")

    rows = db.execute(
        text("""
            SELECT id, goal_id, iteration_number, solution_id, score,
                   status, ai_analysis, ai_discussion,
                   started_at, completed_at, created_at, updated_at
            FROM goal_iterations
            WHERE goal_id = :gid
            ORDER BY iteration_number ASC
        """),
        {"gid": goal_id}
    ).mappings().fetchall()

    iterations = []
    for r in rows:
        iterations.append({
            "id": r.get("id"),
            "iteration_number": r.get("iteration_number"),
            "solution_id": r.get("solution_id"),
            "score": r.get("score"),
            "status": r.get("status"),
            "ai_analysis": r.get("ai_analysis"),
            "ai_discussion": _parse_discussion_list(r.get("ai_discussion")),
            "started_at": r.get("started_at"),
            "completed_at": r.get("completed_at"),
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"),
        })

    return iterations

@router.post("/goals/{goal_id}/iterations/{iter_id}/analysis")

def generate_analysis(goal_id: str, iter_id: str, db: Session = Depends(get_db)):
    """
    生成 AI 分析。
    基于 solutions 和 iteration_constraints 自动生成分析和建议（MVP: 硬编码规则）。
    返回: {"analysis": "本轮分析...", "suggestion": "建议下一轮..."}
    """
    # 验证迭代记录存在
    iter_row = db.execute(
        text("SELECT id FROM goal_iterations WHERE id = :id AND goal_id = :gid"),
        {"id": iter_id, "gid": goal_id}
    ).fetchone()
    if not iter_row:
        raise HTTPException(status_code=404, detail="Iteration not found")

    # 生成 AI 分析
    result = _generate_ai_analysis(goal_id, iter_id, db)

    # 更新迭代记录的 ai_analysis 字段
    analysis_text = f"[分析]\n{result['analysis']}\n\n[建议]\n{result['suggestion']}"
    now_iso = datetime.utcnow().isoformat()

    db.execute(
        text("""
            UPDATE goal_iterations
            SET ai_analysis = :analysis, updated_at = :updated_at
            WHERE id = :id
        """),
        {"analysis": analysis_text, "updated_at": now_iso, "id": iter_id}
    )
    db.commit()

    return result

@router.post("/goals/{goal_id}/iterations/{iter_id}/discuss")

def send_discussion(goal_id: str, iter_id: str, req: DiscussRequest, db: Session = Depends(get_db)):
    """
    发送讨论消息。
    1. 把人的消息追加到 ai_discussion
    2. AI 生成回复（关键词匹配 + 模板，MVP）
    3. 把 AI 回复也追加到 ai_discussion
    4. 如果是人的消息且包含共识关键词，自动触发共识检测 → 更新约束 + 创建下一轮迭代
    5. 返回完整对话列表 + 共识状态
    """
    # 验证迭代记录存在
    iter_row = db.execute(
        text("SELECT ai_discussion FROM goal_iterations WHERE id = :id AND goal_id = :gid"),
        {"id": iter_id, "gid": goal_id}
    ).mappings().fetchone()
    if not iter_row:
        raise HTTPException(status_code=404, detail="Iteration not found")

    # 解析已有对话
    discussion = _parse_discussion_list(iter_row.get("ai_discussion"))

    # 追加人的消息
    now_iso = datetime.utcnow().isoformat()
    human_msg = {
        "role": req.role,
        "content": req.content,
        "timestamp": now_iso,
    }
    discussion.append(human_msg)

    # AI 生成回复
    ai_reply = _generate_ai_reply(req.content, goal_id, db)
    ai_msg = {
        "role": "ai",
        "content": ai_reply,
        "timestamp": datetime.utcnow().isoformat(),
    }
    discussion.append(ai_msg)

    # 保存到数据库
    db.execute(
        text("""
            UPDATE goal_iterations
            SET ai_discussion = :discussion, updated_at = :updated_at
            WHERE id = :id
        """),
        {
            "discussion": json.dumps(discussion, ensure_ascii=False),
            "updated_at": datetime.utcnow().isoformat(),
            "id": iter_id,
        }
    )
    db.commit()

    # Sprint 78: 检测共识并自动应用（仅当发送方为 human 时）
    consensus_result = None
    if req.role == "human" and _detect_consensus(discussion):
        try:
            consensus_result = _apply_consensus(goal_id, iter_id, db)
            logger.info(f"[discuss] Consensus auto-triggered for goal={goal_id}, iter={iter_id}")
        except Exception as e:
            logger.error(f"[discuss] Consensus auto-trigger failed: {e}")
            consensus_result = {"consensus": True, "error": str(e)}

    response: Dict[str, Any] = {"discussion": discussion}
    if consensus_result:
        response["consensus"] = consensus_result
        # 添加标记，方便前端识别
        response["consensus_detected"] = True

    return response

