"""
Sprint 26: Workflow 裁剪修正 — Workflow DAG 编辑 API

此文件为 facade，仅负责路由注册和请求转发。
业务逻辑已拆分至 workflow_edit_logic.py
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import uuid

from reins.common.database import get_db_manager

router = APIRouter(prefix="/api/v1/workflows", tags=["workflow-edit"])

# 延迟导入 logic
_logic = None

def _get_logic():
    global _logic
    if _logic is None:
        from reins.api.workflow_edit_logic import WorkflowEditLogic
        _logic = WorkflowEditLogic()
    return _logic

# ============================================================================
# 请求模型
# ============================================================================

class AddNodeRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    node_type: str = "execution"
    dependencies: List[str] = Field(default_factory=list)
    assignee: Optional[str] = None

class UpdateNodeRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    node_type: Optional[str] = None
    assignee: Optional[str] = None

class AddEdgeRequest(BaseModel):
    source: str
    target: str
    label: Optional[str] = None

class ReorderRequest(BaseModel):
    node_ids: List[str]

class EditActionRequest(BaseModel):
    action: str
    node: Optional[Dict[str, Any]] = None
    node_id: Optional[str] = None
    updates: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    target: Optional[str] = None

class DagEditResponse(BaseModel):
    workflow_id: str
    name: str
    status: str
    dag: Dict[str, Any]
    steps_synced: int = 0

# ============================================================================
# API 端点
# ============================================================================

@router.patch("/{workflow_id}/dag")
def edit_workflow_dag(workflow_id: str, req: EditActionRequest):
    """Workflow DAG 统一编辑接口"""
    return _get_logic().edit_workflow_dag(workflow_id, req)

@router.post("/{workflow_id}/dag/nodes", response_model=DagEditResponse)
def add_workflow_node(workflow_id: str, req: AddNodeRequest):
    """添加 Workflow 节点"""
    return _get_logic().add_workflow_node(workflow_id, req)

@router.patch("/{workflow_id}/dag/nodes/{node_id}", response_model=DagEditResponse)
def update_workflow_node(workflow_id: str, node_id: str, req: UpdateNodeRequest):
    """更新 Workflow 节点属性"""
    return _get_logic().update_workflow_node(workflow_id, node_id, req)

@router.delete("/{workflow_id}/dag/nodes/{node_id}", response_model=DagEditResponse)
def delete_workflow_node(workflow_id: str, node_id: str):
    """删除 Workflow 节点"""
    return _get_logic().delete_workflow_node(workflow_id, node_id)

@router.post("/{workflow_id}/dag/edges", response_model=DagEditResponse)
def add_workflow_edge(workflow_id: str, req: AddEdgeRequest):
    """添加 Workflow 边"""
    return _get_logic().add_workflow_edge(workflow_id, req)

@router.delete("/{workflow_id}/dag/edges/{source}/{target}", response_model=DagEditResponse)
def delete_workflow_edge(workflow_id: str, source: str, target: str):
    """删除 Workflow 边"""
    return _get_logic().delete_workflow_edge(workflow_id, source, target)

@router.post("/{workflow_id}/dag/reorder", response_model=DagEditResponse)
def reorder_workflow_nodes(workflow_id: str, req: ReorderRequest):
    """重排 Workflow 节点顺序"""
    return _get_logic().reorder_workflow_nodes(workflow_id, req)