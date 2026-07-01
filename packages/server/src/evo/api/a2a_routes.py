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
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from models import A2AMessage, Agent
from reins.common.database import get_db_session

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


def _a2a_to_dict(msg: A2AMessage) -> dict:
    """将 A2AMessage ORM 对象转为 dict，自动解析 JSON 列"""
    def _parse_json(value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return None
        return value

    return {
        "id": msg.id,
        "source_agent_id": msg.source_agent_id,
        "target_agent_id": msg.target_agent_id,
        "message": msg.message,
        "channel": msg.channel,
        "priority": msg.priority,
        "status": msg.status,
        "metadata": _parse_json(msg.metadata),
        "requires_ack": msg.requires_ack,
        "ack_status": msg.ack_status,
        "ack_response": msg.ack_response,
        "created_at": msg.created_at.isoformat() if isinstance(msg.created_at, datetime) else str(msg.created_at) if msg.created_at else None,
        "delivered_at": msg.delivered_at.isoformat() if isinstance(msg.delivered_at, datetime) else str(msg.delivered_at) if msg.delivered_at else None,
        "ack_at": msg.ack_at.isoformat() if isinstance(msg.ack_at, datetime) else str(msg.ack_at) if msg.ack_at else None,
    }


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
    db = get_db_session()
    try:
        # 验证源 Agent 存在
        source_row = db.query(Agent).with_entities(Agent.id, Agent.name).filter(
            Agent.id == req.source_agent_id
        ).first()

        if source_row is None:
            raise HTTPException(status_code=404, detail=f"Source agent not found: {req.source_agent_id}")

        # 确定目标 Agent
        if req.target_agents:
            # 验证目标 Agent 存在
            target_rows = db.query(Agent).with_entities(Agent.id, Agent.name).filter(
                Agent.id.in_(req.target_agents)
            ).all()
            target_agents = [(r[0], r[1]) for r in target_rows]
        else:
            # 广播给所有在线 Agent（排除自己）
            target_rows = db.query(Agent).with_entities(Agent.id, Agent.name).filter(
                Agent.status == 'online',
                Agent.id != req.source_agent_id,
            ).all()
            target_agents = [(r[0], r[1]) for r in target_rows]

        if not target_agents:
            return {"broadcast_id": None, "delivered_count": 0, "target_agents": [],
                    "message": "No target agents found"}

        # 创建广播记录（为每个目标创建一条消息）
        broadcast_id = f"bcast-{uuid.uuid4().hex[:12]}"
        now = datetime.now()
        delivered_count = 0

        for target_id, target_name in target_agents:
            message_id = f"a2a-{uuid.uuid4().hex[:12]}"
            db.add(A2AMessage(
                id=message_id,
                broadcast_id=broadcast_id,
                source_agent_id=req.source_agent_id,
                target_agent_id=target_id,
                message=req.message,
                channel=req.channel or "default",
                priority=req.priority or "normal",
                status='pending',
                metadata=json.dumps(req.metadata, ensure_ascii=False) if req.metadata else None,
                requires_ack=req.requires_ack or False,
                created_at=now,
            ))
            delivered_count += 1

        db.commit()
        logger.info(
            "Broadcast %s from %s to %d agents (channel=%s)",
            broadcast_id, req.source_agent_id, delivered_count, req.channel,
        )

        return {
            "broadcast_id": broadcast_id,
            "delivered_count": delivered_count,
            "target_agents": [tid for tid, _ in target_agents],
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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
    db = get_db_session()
    try:
        query = db.query(A2AMessage)
        count_query = db.query(A2AMessage)

        if agent_id:
            query = query.filter(or_(
                A2AMessage.source_agent_id == agent_id,
                A2AMessage.target_agent_id == agent_id,
            ))
            count_query = count_query.filter(or_(
                A2AMessage.source_agent_id == agent_id,
                A2AMessage.target_agent_id == agent_id,
            ))

        if target_agent_id:
            query = query.filter(A2AMessage.target_agent_id == target_agent_id)
            count_query = count_query.filter(A2AMessage.target_agent_id == target_agent_id)

        if source_agent_id:
            query = query.filter(A2AMessage.source_agent_id == source_agent_id)
            count_query = count_query.filter(A2AMessage.source_agent_id == source_agent_id)

        if channel:
            query = query.filter(A2AMessage.channel == channel)
            count_query = count_query.filter(A2AMessage.channel == channel)

        if status:
            query = query.filter(A2AMessage.status == status)
            count_query = count_query.filter(A2AMessage.status == status)

        if broadcast_id:
            query = query.filter(A2AMessage.broadcast_id == broadcast_id)
            count_query = count_query.filter(A2AMessage.broadcast_id == broadcast_id)

        total = count_query.count()

        offset = (page - 1) * page_size
        rows = query.order_by(A2AMessage.created_at.desc()).offset(offset).limit(page_size).all()
        items = [_a2a_to_dict(r) for r in rows]

        return A2AMessageListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    finally:
        db.close()


# ===========================================================================
# POST /api/v1/a2a/messages — 创建 A2A 消息
# ===========================================================================

@router.post("/messages")
def create_a2a_message(req: A2AMessageCreate):
    """
    创建一条 Agent 间消息。
    """
    db = get_db_session()
    try:
        # 验证源 Agent 存在
        source_row = db.query(Agent).filter(Agent.id == req.source_agent_id).first()
        if source_row is None:
            raise HTTPException(status_code=404, detail=f"Source agent not found: {req.source_agent_id}")

        # 验证目标 Agent 存在
        target_row = db.query(Agent).filter(Agent.id == req.target_agent_id).first()
        if target_row is None:
            raise HTTPException(status_code=404, detail=f"Target agent not found: {req.target_agent_id}")

        message_id = f"a2a-{uuid.uuid4().hex[:12]}"
        now = datetime.now()

        msg = A2AMessage(
            id=message_id,
            source_agent_id=req.source_agent_id,
            target_agent_id=req.target_agent_id,
            message=req.message,
            channel=req.channel or "default",
            priority=req.priority or "normal",
            status='pending',
            metadata=json.dumps(req.metadata, ensure_ascii=False) if req.metadata else None,
            requires_ack=req.requires_ack,
            created_at=now,
        )
        db.add(msg)
        db.commit()

        logger.info(
            "A2A message %s: %s -> %s (channel=%s)",
            message_id, req.source_agent_id, req.target_agent_id, req.channel,
        )

        return _a2a_to_dict(msg)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
