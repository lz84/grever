"""
Sprint 27: 争议管理 — 争议 CRUD + 讨论/仲裁 API

此文件为 facade，仅负责路由注册和请求转发。
业务逻辑已拆分至 dispute_logic.py

⚠️ 所有路由使用 Depends(get_db) 注入 session，不创建自己的 session。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import uuid

from reins.common.database import get_db
from persistence.tables import disputes as disputes_table

router = APIRouter(prefix="/api/v1/disputes", tags=["dispute-manage"])

# 延迟导入 logic
_logic = None

def _get_logic():
    global _logic
    if _logic is None:
        from evo.api.dispute_logic import DisputeLogic
        _logic = DisputeLogic()
    return _logic

# ============================================================================
# 请求/响应模型
# ============================================================================

class DisputeCreate(BaseModel):
    dispute_type: str
    description: str
    involved_agents: List[str]
    related_task_id: Optional[str] = None
    goal_id: Optional[str] = None
    raised_by_agent: Optional[str] = None

class DisputeResponse(BaseModel):
    id: str
    dispute_type: Optional[str]
    description: str
    involved_agents: List[str]
    related_task_id: Optional[str]
    goal_id: Optional[str] = None
    status: str
    resolution: Optional[str]
    resolved_by: Optional[str]
    created_at: str
    updated_at: str
    resolved_at: Optional[str]

class DiscussRequest(BaseModel):
    agent_id: str
    message: str

class UpdateStatusRequest(BaseModel):
    new_status: str

class ArbitrateRequest(BaseModel):
    resolution: str
    arbitrator: str = "human"

class TimelineEntry(BaseModel):
    timestamp: str
    agent_id: str
    action: str
    message: str
    metadata: Optional[Dict[str, Any]] = None

class DisputeDetailResponse(BaseModel):
    id: str
    dispute_type: str
    description: str
    involved_agents: List[str]
    related_task_id: Optional[str]
    status: str
    raised_by_agent: Optional[str]
    resolution: Optional[str]
    resolved_by: Optional[str]
    created_at: str
    updated_at: str
    resolved_at: Optional[str]
    deadline: Optional[str]
    discussion_count: int = 0

class TimelineResponse(BaseModel):
    dispute_id: str
    entries: List[TimelineEntry]

class DisputeStatsResponse(BaseModel):
    total: int
    open: int
    discussing: int
    resolved: int
    escalated: int
    closed: int
    by_type: Dict[str, int]

# ============================================================================
# CRUD 路由 — 全部使用 Depends(get_db) 注入 session
# ============================================================================

@router.post("/", response_model=DisputeResponse)
def raise_dispute(req: DisputeCreate, db: Session = Depends(get_db)):
    """发起争议"""
    return _get_logic().raise_dispute(db, req)

@router.get("/", response_model=List[DisputeResponse])
def list_disputes(status: Optional[str] = None, goal_id: Optional[str] = None, db: Session = Depends(get_db)):
    """列出争议"""
    return _get_logic().list_disputes(db, status, goal_id)

@router.get("/stats", response_model=DisputeStatsResponse)
def get_dispute_stats(db: Session = Depends(get_db)):
    """争议统计"""
    return _get_logic().get_dispute_stats(db)

@router.get("/{dispute_id}", response_model=DisputeResponse)
def get_dispute(dispute_id: str, db: Session = Depends(get_db)):
    """获取争议"""
    return _get_logic().get_dispute(db, dispute_id)

@router.patch("/{dispute_id}/resolve")
def resolve_dispute(dispute_id: str, resolution: str, resolved_by: Optional[str] = None, db: Session = Depends(get_db)):
    """解决争议"""
    return _get_logic().resolve_dispute(db, dispute_id, resolution, resolved_by)

@router.post("/{dispute_id}/discuss")
def add_discussion(dispute_id: str, req: DiscussRequest, db: Session = Depends(get_db)):
    """Agent 添加讨论消息"""
    return _get_logic().add_discussion(db, dispute_id, req)

@router.patch("/{dispute_id}/status")
def update_dispute_status(dispute_id: str, req: UpdateStatusRequest, db: Session = Depends(get_db)):
    """更新争议状态"""
    return _get_logic().update_dispute_status(db, dispute_id, req)

@router.post("/{dispute_id}/arbitrate")
def arbitrate_dispute(dispute_id: str, req: ArbitrateRequest, db: Session = Depends(get_db)):
    """人类仲裁"""
    return _get_logic().arbitrate_dispute(db, dispute_id, req)

@router.get("/{dispute_id}/timeline", response_model=TimelineResponse)
def get_dispute_timeline(dispute_id: str, db: Session = Depends(get_db)):
    """获取争议讨论时间线"""
    return _get_logic().get_dispute_timeline(db, dispute_id)

@router.get("/{dispute_id}/detail", response_model=DisputeDetailResponse)
def get_dispute_detail(dispute_id: str, db: Session = Depends(get_db)):
    """获取争议详情（含讨论计数）"""
    return _get_logic().get_dispute_detail(db, dispute_id)
