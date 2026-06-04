"""
Evo 进化域 - A2A (Agent-to-Agent) Hub API

提供 Agent 间广播和消息传递端点。
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

router = APIRouter(prefix="/api/v1/a2a", tags=["a2a-hub"])

# ===========================================================================
# 请求/响应模型
# ===========================================================================


class BroadcastRequest(BaseModel):
    """广播请求"""
    source_agent_id: str
    message: str
    channel: Optional[str] = "default"
    priority: Optional[str] = "normal"  # low / normal / high / urgent
    metadata: Optional[dict] = None
    target_agents: Optional[list[str]] = None  # None = 广播给所有
    requires_ack: Optional[bool] = False


class A2AMessageCreate(BaseModel):
    """创建 A2A 消息请求"""
    source_agent_id: str
    target_agent_id: str
    message: str
    channel: Optional[str] = "default"
    priority: Optional[str] = "normal"
    metadata: Optional[dict] = None
    requires_ack: Optional[bool] = False


class A2AMessageAckRequest(BaseModel):
    """消息确认请求"""
    status: str = "read"  # read / processed / rejected
    response: Optional[str] = None


class A2AMessageListResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int


class BroadcastResponse(BaseModel):
    broadcast_id: str
    delivered_count: int
    target_agents: list[str]


# ===========================================================================
# 辅助函数
# ===========================================================================

MESSAGE_COLUMNS = [
    "id", "source_agent_id", "target_agent_id", "message", "channel",
    "priority", "status", "metadata", "requires_ack", "ack_status",
    "ack_response", "created_at", "delivered_at", "ack_at",
]


def _row_to_dict(row) -> dict:
    """将 SQLAlchemy Row 转为 dict，自动解析 JSON 列和 DateTime"""
    d = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    for json_col in ("metadata",):
        val = d.get(json_col)
        if isinstance(val, str):
            try:
                d[json_col] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                d[json_col] = None
        elif val is None:
            d[json_col] = None
    for dt_col in ("created_at", "delivered_at", "ack_at"):
        val = d.get(dt_col)
        if val is not None and not isinstance(val, str):
            d[dt_col] = str(val)
    return d


# ===========================================================================
# POST /api/v1/a2a/broadcast — Agent 间广播
# ===========================================================================

@router.post("/broadcast")
def broadcast_message(req: BroadcastRequest):
    """
    向多个 Agent 广播消息。

    - 如果指定 target_agents，只发送给这些 Agent
    - 否则发送给所有在线 Agent
    """
    db = get_db_manager()

    # 验证源 Agent 存在
    with db.engine.connect() as conn:
        source_row = source_row = conn.execute(
        text("SELECT id, name FROM agents WHERE id = :id"),
        {"id": req.source_agent_id},
        ).fetchone()

    if source_row is None:
        raise HTTPException(status_code=404, detail=f"Source agent not found: {req.source_agent_id}")

    # 确定目标 Agent
    if req.target_agents:
        # 验证目标 Agent 存在
        placeholders = ", ".join(f":aid{i}" for i in range(len(req.target_agents)))
        agent_params = {f"aid{i}": aid for i, aid in enumerate(req.target_agents)}
        with db.engine.connect() as conn:
            target_rows = target_rows = conn.execute(
            text(f"SELECT id, name FROM agents WHERE id IN ({placeholders})"),
            agent_params,
            ).fetchall()
        target_agents = [(r.id, r.name) for r in target_rows]
    else:
        # 广播给所有在线 Agent（排除自己）
        with db.engine.connect() as conn:
            target_rows = target_rows = conn.execute(
            text("SELECT id, name FROM agents WHERE status = 'online' AND id != :id"),
            {"id": req.source_agent_id},
            ).fetchall()
        target_agents = [(r.id, r.name) for r in target_rows]

    if not target_agents:
        return {"broadcast_id": None, "delivered_count": 0, "target_agents": [],
                "message": "No target agents found"}

    # 创建广播记录（为每个目标创建一条消息）
    broadcast_id = f"bcast-{uuid.uuid4().hex[:12]}"
    now = datetime.now().isoformat()
    delivered_count = 0

    for target_id, target_name in target_agents:
        message_id = f"a2a-{uuid.uuid4().hex[:12]}"
        with db.engine.connect() as conn:
            conn.execute(
            text("""
            INSERT INTO a2a_messages (
            id, broadcast_id, source_agent_id, target_agent_id,
            message, channel, priority, status, metadata,
            requires_ack, created_at
            ) VALUES (
            :id, :broadcast_id, :source_agent_id, :target_agent_id,
            :message, :channel, :priority, 'pending', :metadata,
            :requires_ack, :created_at
            )
            """),
            {
            "id": message_id,
            "broadcast_id": broadcast_id,
            "source_agent_id": req.source_agent_id,
            "target_agent_id": target_id,
            "message": req.message,
            "channel": req.channel or "default",
            "priority": req.priority or "normal",
            "metadata": json.dumps(req.metadata, ensure_ascii=False) if req.metadata else None,
            "requires_ack": req.requires_ack if hasattr(req, 'requires_ack') else False,
            "created_at": now,
            },
            )
            conn.commit()
        delivered_count += 1

    logger.info(
        "Broadcast %s from %s to %d agents (channel=%s)",
        broadcast_id, req.source_agent_id, delivered_count, req.channel,
    )

    return {
        "broadcast_id": broadcast_id,
        "delivered_count": delivered_count,
        "target_agents": [tid for tid, _ in target_agents],
    }


# ===========================================================================
# GET /api/v1/a2a/messages — 查询 A2A 消息列表
# ===========================================================================

@router.get("/messages")
def list_a2a_messages(
    agent_id: Optional[str] = Query(None, description="按 Agent ID 过滤（源或目标）"),
    target_agent_id: Optional[str] = Query(None, description="按目标 Agent ID 过滤"),
    source_agent_id: Optional[str] = Query(None, description="按源 Agent ID 过滤"),
    channel: Optional[str] = Query(None, description="按频道过滤"),
    status: Optional[str] = Query(None, description="按状态过滤: pending/delivered/read/processed/rejected"),
    broadcast_id: Optional[str] = Query(None, description="按广播 ID 过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """查询 A2A 消息列表，支持多种过滤条件"""
    where_clauses = []
    params: dict = {}

    if agent_id:
        where_clauses.append("(source_agent_id = :agent_id OR target_agent_id = :agent_id)")
        params["agent_id"] = agent_id

    if target_agent_id:
        where_clauses.append("target_agent_id = :target_agent_id")
        params["target_agent_id"] = target_agent_id

    if source_agent_id:
        where_clauses.append("source_agent_id = :source_agent_id")
        params["source_agent_id"] = source_agent_id

    if channel:
        where_clauses.append("channel = :channel")
        params["channel"] = channel

    if status:
        where_clauses.append("status = :status")
        params["status"] = status

    if broadcast_id:
        where_clauses.append("broadcast_id = :broadcast_id")
        params["broadcast_id"] = broadcast_id

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    cols = ", ".join(MESSAGE_COLUMNS)
    db = get_db_manager()

    # 总数查询
    count_sql = f"SELECT COUNT(*) FROM a2a_messages {where_sql}"
    with db.engine.connect() as conn:
        total = total = conn.execute(text(count_sql), params).scalar()

    # 分页查询
    offset = (page - 1) * page_size
    data_sql = (
        f"SELECT {cols} FROM a2a_messages {where_sql} "
        "ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    )
    params["limit"] = page_size
    params["offset"] = offset

    with db.engine.connect() as conn:
        rows = rows = conn.execute(text(data_sql), params).fetchall()
    items = [_row_to_dict(r) for r in rows]

    return A2AMessageListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ===========================================================================
# POST /api/v1/a2a/messages — 创建 A2A 消息
# ===========================================================================

@router.post("/messages")
def create_a2a_message(req: A2AMessageCreate):
    """
    创建一条 Agent 间消息。
    """
    db = get_db_manager()

    # 验证源 Agent 存在
    with db.engine.connect() as conn:
        source_row = source_row = conn.execute(
        text("SELECT id FROM agents WHERE id = :id"),
        {"id": req.source_agent_id},
        ).fetchone()
    if source_row is None:
        raise HTTPException(status_code=404, detail=f"Source agent not found: {req.source_agent_id}")

    # 验证目标 Agent 存在
    with db.engine.connect() as conn:
        target_row = target_row = conn.execute(
        text("SELECT id FROM agents WHERE id = :id"),
        {"id": req.target_agent_id},
        ).fetchone()
    if target_row is None:
        raise HTTPException(status_code=404, detail=f"Target agent not found: {req.target_agent_id}")

    message_id = f"a2a-{uuid.uuid4().hex[:12]}"
    now = datetime.now().isoformat()

    with db.engine.connect() as conn:
        conn.execute(
        text("""
        INSERT INTO a2a_messages (
        id, source_agent_id, target_agent_id, message, channel,
        priority, status, metadata, requires_ack, created_at
        ) VALUES (
        :id, :source_agent_id, :target_agent_id, :message, :channel,
        :priority, 'pending', :metadata, :requires_ack, :created_at
        )
        """),
        {
        "id": message_id,
        "source_agent_id": req.source_agent_id,
        "target_agent_id": req.target_agent_id,
        "message": req.message,
        "channel": req.channel or "default",
        "priority": req.priority or "normal",
        "metadata": json.dumps(req.metadata, ensure_ascii=False) if req.metadata else None,
        "requires_ack": req.requires_ack,
        "created_at": now,
        },
        )
        conn.commit()

    logger.info(
        "A2A message %s: %s -> %s (channel=%s)",
        message_id, req.source_agent_id, req.target_agent_id, req.channel,
    )

    cols = ", ".join(MESSAGE_COLUMNS)
    with db.engine.connect() as conn:
        created = created = conn.execute(
        text(f"SELECT {cols} FROM a2a_messages WHERE id = :id"),
        {"id": message_id},
        ).fetchone()

    return _row_to_dict(created)
