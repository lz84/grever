"""
Vigil 信任评估 API

提供信任评分计算和查询端点。
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from models import TrustEvaluation, Agent, Task
from reins.common.database import get_db_session
from persistence.tables import disputes as disputes_table, heartbeat_logs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/vigil/trust", tags=["vigil-trust"])

# ===========================================================================
# 请求/响应模型
# ===========================================================================


class TrustScoreUpdate(BaseModel):
    """更新信任评分请求"""
    score: float
    reason: Optional[str] = None
    category: Optional[str] = None  # task_completion / communication / security / collaboration


class TrustHistoryResponse(BaseModel):
    agent_id: str
    current_score: float
    history: list[dict]
    total_records: int


class TrustScoreResponse(BaseModel):
    agent_id: str
    score: float
    level: str  # trusted / neutral / suspicious / blocked
    last_updated: Optional[str] = None
    total_evaluations: int = 0


# ===========================================================================
# 辅助函数
# ===========================================================================

TRUST_LEVELS = {
    "trusted": (0.8, 1.0),
    "neutral": (0.4, 0.8),
    "suspicious": (0.2, 0.4),
    "blocked": (0.0, 0.2),
}


def _get_trust_level(score: float) -> str:
    """根据评分确定信任等级"""
    for level, (low, high) in TRUST_LEVELS.items():
        if low <= score < high:
            return level
    return "blocked"


def _calculate_trust_score(agent_id: str) -> float:
    """
    计算 Agent 的综合信任评分。

    基于：
    - 任务完成率
    - 历史行为记录
    - 争议记录
    """
    db = get_db_session()
    try:
        # 1. 任务完成率 (权重 40%)
        total_tasks = db.query(func.count(Task.id)).filter(
            Task.assigned_agent == agent_id
        ).scalar() or 0
        completed_tasks = db.query(func.count(Task.id)).filter(
            Task.assigned_agent == agent_id,
            Task.status.in_(['completed', 'success'])
        ).scalar() or 0

        task_score = 0.5  # 默认中立
        if total_tasks > 0:
            task_score = completed_tasks / total_tasks

        # 2. 争议记录 (权重 30%) - 越少越好
        # Use Core Table for disputes (JSON column with LIKE pattern)
        dispute_query = select(func.count()).select_from(disputes_table).where(
            disputes_table.c.involved_agents.like(f"%{agent_id}%")
        )
        dispute_count = db.execute(dispute_query).scalar() or 0

        dispute_score = max(0, 1.0 - (dispute_count * 0.1))

        # 3. 心跳稳定性 (权重 30%) - Use Core Table
        total_hb_query = select(func.count()).select_from(heartbeat_logs).where(
            heartbeat_logs.c.agent_id == agent_id
        )
        total_hb = db.execute(total_hb_query).scalar() or 0

        online_hb_query = select(func.count()).select_from(heartbeat_logs).where(
            heartbeat_logs.c.agent_id == agent_id,
            heartbeat_logs.c.status == 'online'
        )
        online_hb = db.execute(online_hb_query).scalar() or 0

        heartbeat_score = 0.5
        if total_hb > 0:
            heartbeat_score = online_hb / total_hb

        # 综合评分
        final_score = (task_score * 0.4) + (dispute_score * 0.3) + (heartbeat_score * 0.3)
        return round(min(1.0, max(0.0, final_score)), 4)
    finally:
        db.close()


# ===========================================================================
# GET /api/v1/vigil/trust/agents/{agent_id} — 查询信任评分
# ===========================================================================

@router.get("/agents/{agent_id}")
def get_trust_score(agent_id: str):
    """
    查询指定 Agent 的当前信任评分。

    评分基于任务完成率、争议记录和心跳稳定性综合计算。
    """
    db = get_db_session()
    try:
        # 验证 Agent 存在
        agent_row = db.query(Agent).with_entities(Agent.id, Agent.name, Agent.status).filter(
            Agent.id == agent_id
        ).first()

        if agent_row is None:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

        # 计算信任评分
        score = _calculate_trust_score(agent_id)
        level = _get_trust_level(score)

        # 统计评估次数
        eval_count = db.query(func.count(TrustEvaluation.id)).filter(
            TrustEvaluation.agent_id == agent_id
        ).scalar() or 0

        # 获取最后更新时间
        last_updated_row = db.query(TrustEvaluation.created_at).filter(
            TrustEvaluation.agent_id == agent_id
        ).order_by(TrustEvaluation.created_at.desc()).first()

        last_updated = None
        if last_updated_row:
            val = last_updated_row[0]
            last_updated = str(val) if val else None

        return {
            "agent_id": agent_id,
            "agent_name": agent_row[1],
            "score": score,
            "level": level,
            "last_updated": last_updated,
            "total_evaluations": eval_count,
        }
    finally:
        db.close()


# ===========================================================================
# POST /api/v1/vigil/trust/agents/{agent_id} — 更新信任评分
# ===========================================================================

@router.post("/agents/{agent_id}")
def update_trust_score(agent_id: str, req: TrustScoreUpdate):
    """
    手动更新 Agent 的信任评分。

    用于人工评估或自动化信任调整。
    """
    if not 0 <= req.score <= 1:
        raise HTTPException(status_code=400, detail="Score must be between 0 and 1")

    db = get_db_session()
    try:
        # 验证 Agent 存在
        agent_row = db.query(Agent).with_entities(Agent.id, Agent.name).filter(
            Agent.id == agent_id
        ).first()

        if agent_row is None:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

        # 记录评估
        eval_id = str(uuid.uuid4())
        now = datetime.now()
        level = _get_trust_level(req.score)

        db.add(TrustEvaluation(
            id=eval_id,
            agent_id=agent_id,
            score=req.score,
            level=level,
            reason=req.reason,
            category=req.category,
            created_at=now,
        ))
        db.commit()

        logger.info(
            "Trust score updated for agent %s: %.2f (level=%s, reason=%s)",
            agent_id, req.score, level, req.reason,
        )

        return {
            "agent_id": agent_id,
            "score": req.score,
            "level": level,
            "evaluation_id": eval_id,
            "updated_at": now.isoformat(),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ===========================================================================
# GET /api/v1/vigil/trust/agents/{agent_id}/history — 信任历史
# ===========================================================================

@router.get("/agents/{agent_id}/history")
def get_trust_history(
    agent_id: str,
    limit: int = Query(50, ge=1, le=200, description="返回记录数"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """
    查询 Agent 的信任评分历史记录。
    """
    db = get_db_session()
    try:
        # 验证 Agent 存在
        agent_row = db.query(Agent).with_entities(Agent.id, Agent.name).filter(
            Agent.id == agent_id
        ).first()

        if agent_row is None:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

        # 获取历史记录
        rows = db.query(TrustEvaluation).with_entities(
            TrustEvaluation.id, TrustEvaluation.score, TrustEvaluation.level,
            TrustEvaluation.reason, TrustEvaluation.category, TrustEvaluation.created_at,
        ).filter(
            TrustEvaluation.agent_id == agent_id
        ).order_by(
            TrustEvaluation.created_at.desc()
        ).limit(limit).offset(offset).all()

        history = []
        for r in rows:
            history.append({
                "id": r[0],
                "score": r[1],
                "level": r[2],
                "reason": r[3],
                "category": r[4],
                "created_at": str(r[5]) if r[5] else None,
            })

        # 总数
        total = db.query(func.count(TrustEvaluation.id)).filter(
            TrustEvaluation.agent_id == agent_id
        ).scalar() or 0

        # 当前评分
        current_score = _calculate_trust_score(agent_id)

        return {
            "agent_id": agent_id,
            "current_score": current_score,
            "history": history,
            "total_records": total,
        }
    finally:
        db.close()