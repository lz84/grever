"""
Workflow API 路由（MAK-233: 工作流引擎与派发集成）

功能：
1. Workflow 列表（GET /）
2. Workflow 激活 → Task 创建（POST /activate）
3. Task 完成 → Workflow 更新（通过监听 task_completed 事件）
4. workflow_progress 实时追踪（GET /progress）

此文件为 facade，仅负责路由注册和请求转发。
业务逻辑已拆分至 workflows_logic.py
"""

from loguru import logger

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json
from pydantic import BaseModel

from persistence.database import DatabaseManager
from persistence.repository import WorkflowRepository, WorkflowStepRepository
from persistence.tables import workflows, workflow_steps, tasks
from models import WorkflowStatus, WorkflowStepStatus, TaskStatus
from reins.core.assignment import get_agent_registry, get_task_assigner
from models.task import Task
from reins.common.database import get_db
from api.app_state import get_db_manager
from reins.common.event_bus import WorkflowEvent, get_event_bus
from shared.eventbus.manager import get_event_bus_manager

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])

# 延迟导入 logic 模块，避免循环依赖
_logic_module = None

def _get_logic():
    global _logic_module
    if _logic_module is None:
        from reins.api.workflows_logic import WorkflowsLogic
        _logic_module = WorkflowsLogic(get_db_manager())
    return _logic_module

def emit_workflow_event(event_type: str, workflow_id: str, data: Dict[str, Any] = None):
    """发布 Workflow 事件到 EventBus"""
    try:
        bus_manager = get_event_bus_manager()
        bus = bus_manager.get_adapter(None)
        if bus:
            event = WorkflowEvent(
                event_type=event_type,
                workflow_id=workflow_id,
                step_id="",
                data=data or {},
            )
            bus.publish(event)
    except Exception as e:
        logger.error(f"[Workflow Event] Publish error: {e}")

# ============================================================================
# 0. Workflow 列表
# ============================================================================

@router.get("/")
def list_workflows(
    status: Optional[str] = None,
    goal_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    """列出 Workflow，支持分页和筛选"""
    db_manager = get_db_manager()
    repo = WorkflowRepository(db_manager.engine)
    all_items = repo.list(status=status, goal_id=goal_id)
    total = len(all_items)
    paged = all_items[skip : skip + limit]
    return {
        "workflows": [w.to_dict() for w in paged],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

# ============================================================================
# 1. Workflow 激活 → Task 创建
# ============================================================================

class ActivateWorkflowResponse(BaseModel):
    workflow_id: str
    tasks_created: int
    task_ids: List[str]
    status: str

@router.post("/{workflow_id}/activate", response_model=ActivateWorkflowResponse)
def activate_workflow(workflow_id: str):
    """MA-K233-1:Workflow 激活"""
    return _get_logic().activate_workflow(workflow_id)

# ============================================================================
# 2. Task 完成 → Workflow 更新（事件监听模式）
# ============================================================================

def register_workflow_event_listeners():
    """MA-K233-2: Register Workflow event listeners"""
    _get_logic().register_event_listeners()

# ============================================================================
# 3. workflow_progress 实时追踪
# ============================================================================

class WorkflowProgressResponse(BaseModel):
    workflow_id: str
    completed_steps: int
    total_steps: int
    progress_percent: float
    current_step: Optional[str] = None
    status: str
    steps: List[Dict[str, Any]] = []

@router.get("/{workflow_id}/progress", response_model=WorkflowProgressResponse)
def get_workflow_progress(workflow_id: str):
    """MA-K233-3:获取工作流进度"""
    return _get_logic().get_workflow_progress(workflow_id)
