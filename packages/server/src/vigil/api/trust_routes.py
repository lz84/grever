"""
Vigil 信任评估 API

提供信任评分计算和查询端点。
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from api.app_state import get_db_manager

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
    db = get_db_manager()

    # 1. 任务完成率 (权重 40%)
    with db.engine.connect() as conn:
        task_stats = task_stats = conn.execute(
        text("""
        SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status IN ('completed', 'success') THEN 1 ELSE 0 END) as successful
        FROM tasks
        WHERE assigned_agent = :agent_id
        """),
        {"agent_id": agent_id},
        ).fetchone()

    task_score = 0.5  # 默认中立
    if task_stats and task_stats.total > 0:
        task_score = task_stats.successful / task_stats.total

    # 2. 争议记录 (权重 30%) - 越少越好
    with db.engine.connect() as conn:
        dispute_count = dispute_count = conn.execute(
        text("""
        SELECT COUNT(*) FROM disputes
        WHERE json_extract(involved_agents, '$[*]') LIKE :pattern
        """),
        {"pattern": f"%{agent_id}%"},
        ).scalar() or 0

    dispute_score = max(0, 1.0 - (dispute_count * 0.1))

    # 3. 心跳稳定性 (权重 30%)
    with db.engine.connect() as conn:
        heartbeat_stats = heartbeat_stats = conn.execute(
        text("""
        SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status = 'online' THEN 1 ELSE 0 END) as online
        FROM heartbeat_logs
        WHERE agent_id = :agent_id
        """),
        {"agent_id": agent_id},
        ).fetchone()

    heartbeat_score = 0.5
    if heartbeat_stats and heartbeat_stats.total > 0:
        heartbeat_score = heartbeat_stats.online / heartbeat_stats.total

    # 综合评分
    final_score = (task_score * 0.4) + (dispute_score * 0.3) + (heartbeat_score * 0.3)
    return round(min(1.0, max(0.0, final_score)), 4)


# ===========================================================================
# GET /api/v1/vigil/trust/agents/{agent_id} — 查询信任评分
# ===========================================================================

@router.get("/agents/{agent_id}")
def get_trust_score(agent_id: str):
    """
    查询指定 Agent 的当前信任评分。

    评分基于任务完成率、争议记录和心跳稳定性综合计算。
    """
    db = get_db_manager()

    # 验证 Agent 存在
    with db.engine.connect() as conn:
        agent_row = agent_row = conn.execute(
        text("SELECT id, name, status FROM agents WHERE id = :id"),
        {"id": agent_id},
        ).fetchone()

    if agent_row is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    # 计算信任评分
    score = _calculate_trust_score(agent_id)
    level = _get_trust_level(score)

    # 统计评估次数
    with db.engine.connect() as conn:
        eval_count = eval_count = conn.execute(
        text("SELECT COUNT(*) FROM trust_evaluations WHERE agent_id = :id"),
        {"id": agent_id},
        ).scalar() or 0

    # 获取最后更新时间
    with db.engine.connect() as conn:
        last_updated_row = last_updated_row = conn.execute(
        text("""
        SELECT created_at FROM trust_evaluations
        WHERE agent_id = :id ORDER BY created_at DESC LIMIT 1
        """),
        {"id": agent_id},
        ).fetchone()

    last_updated = None
    if last_updated_row:
        val = last_updated_row[0]
        last_updated = str(val) if val else None

    return {
        "agent_id": agent_id,
        "agent_name": agent_row.name,
        "score": score,
        "level": level,
        "last_updated": last_updated,
        "total_evaluations": eval_count,
    }


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

    db = get_db_manager()

    # 验证 Agent 存在
    with db.engine.connect() as conn:
        agent_row = agent_row = conn.execute(
        text("SELECT id, name FROM agents WHERE id = :id"),
        {"id": agent_id},
        ).fetchone()

    if agent_row is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    # 记录评估
    eval_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    level = _get_trust_level(req.score)

    with db.engine.connect() as conn:
        conn.execute(
        text("""
        INSERT INTO trust_evaluations (
        id, agent_id, score, level, reason, category, created_at
        ) VALUES (
        :id, :agent_id, :score, :level, :reason, :category, :created_at
        )
        """),
        {
        "id": eval_id,
        "agent_id": agent_id,
        "score": req.score,
        "level": level,
        "reason": req.reason,
        "category": req.category,
        "created_at": now,
        },
        )
        conn.commit()

    logger.info(
        "Trust score updated for agent %s: %.2f (level=%s, reason=%s)",
        agent_id, req.score, level, req.reason,
    )

    return {
        "agent_id": agent_id,
        "score": req.score,
        "level": level,
        "evaluation_id": eval_id,
        "updated_at": now,
    }


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
    db = get_db_manager()

    # 验证 Agent 存在
    with db.engine.connect() as conn:
        agent_row = agent_row = conn.execute(
        text("SELECT id, name FROM agents WHERE id = :id"),
        {"id": agent_id},
        ).fetchone()

    if agent_row is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    # 获取历史记录
    with db.engine.connect() as conn:
        rows = rows = conn.execute(
        text("""
        SELECT id, score, level, reason, category, created_at
        FROM trust_evaluations
        WHERE agent_id = :id
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """),
        {"id": agent_id, "limit": limit, "offset": offset},
        ).fetchall()

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
    with db.engine.connect() as conn:
        total = total = conn.execute(
        text("SELECT COUNT(*) FROM trust_evaluations WHERE agent_id = :id"),
        {"id": agent_id},
        ).scalar() or 0

    # 当前评分
    current_score = _calculate_trust_score(agent_id)

    return {
        "agent_id": agent_id,
        "current_score": current_score,
        "history": history,
        "total_records": total,
    }
