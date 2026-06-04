"""
Sprint 29-3: Workflow 对话式编辑 (Facade)

功能:
- POST /api/v1/workflows/{id}/dag(chat
  自然语言指令 → 解析 → 修改 DAG

支持的指令类型:
1. 合并节点
2. 插入节点
3. 删除节点
4. 移动节点
5. 重命名节点
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any
import json

from reins.common.database import get_db
from .workflow_dag_logic import _get_workflow_dag, _save_dag, _validate_dag, _sync_steps, _parse_instruction, _execute_action

router = APIRouter(prefix="/api/v1/workflows", tags=["workflow-dag-chat"])

class DagChatRequest(BaseModel):
    instruction: Optional[str] = Field(None, description="自然语言修改指令")
    message: Optional[str] = Field(None, description="自然语言修改指令（前端别名）")
    preview: bool = Field(False, description="仅预览，不执行修改")

class DagChange(BaseModel):
    action: str = Field(..., description="操作类型")
    detail: str = Field(..., description="操作详情")

class DagChatResponse(BaseModel):
    success: bool
    dag: Optional[Dict[str, Any]] = None
    changes: List[DagChange] = []
    message: str = ""

@router.post("/{workflow_id}/dag/chat", response_model=DagChatResponse)
def workflow_dag_chat(
    workflow_id: str, req: DagChatRequest, db: Session = Depends(get_db)
):
    """Sprint 29-3: Workflow 对话式编辑"""
    wf = _get_workflow_dag(db, workflow_id)
    if not wf:
        raise HTTPException(404, f"Workflow '{workflow_id}' not found")
    
    if wf["status"] not in ("draft", "paused"):
        raise HTTPException(400, f"Workflow 状态为 '{wf['status']}'，仅 draft/paused 状态可编辑")
    
    dag = wf["dag"]
    instruction = req.instruction or req.message or ""
    op = _parse_instruction(instruction, dag)
    
    if op.get("action") == "unknown":
        return DagChatResponse(success=False, message=op.get("message", "无法解析指令"))
    
    new_dag, changes, error = _execute_action(dict(dag), op)
    if error:
        return DagChatResponse(success=False, message=error)
    
    is_valid, err = _validate_dag(new_dag)
    if not is_valid:
        return DagChatResponse(success=False, message=f"操作后 DAG 无效: {err}")
    
    if req.preview:
        return DagChatResponse(success=True, dag=new_dag, changes=changes, message="预览模式，未执行修改")
    
    _save_dag(db, workflow_id, new_dag)
    _sync_steps(db, workflow_id, new_dag)
    db.commit()
    
    return DagChatResponse(success=True, dag=new_dag, changes=changes, message=f"成功执行: {instruction}")
