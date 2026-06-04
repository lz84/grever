"""人类输入 API - Pydantic 模型定义"""
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

from pydantic import BaseModel

from reins.common.database import get_db_manager

class HumanInputRequest(BaseModel):
    """人类输入请求模型"""
    id: str
    task_id: str
    title: str
    description: Optional[str] = None
    input_type: str  # confirmation, approval, data_entry, selection, etc.
    status: str  # pending, submitted, rejected, cancelled
    input_data: Optional[Dict[str, Any]] = None
    submitted_by: Optional[str] = None
    submitted_at: Optional[str] = None
    created_at: str
    updated_at: str
    context: Optional[Dict[str, Any]] = None  # 任务上下文信息

class CreateHumanInputRequest(BaseModel):
    """创建人类输入请求"""
    task_id: str
    title: str
    description: Optional[str] = None
    input_type: str = "confirmation"
    context: Optional[Dict[str, Any]] = None

class SubmitHumanInputRequest(BaseModel):
    """提交人类输入请求 — input_data 可以是 dict 或字符串"""
    input_data: Optional[Union[Dict[str, Any], str]] = None
    submitted_by: str = "anonymous"

class HumanInputResponse(BaseModel):
    """人类输入响应"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class PendingHumanInputResponse(BaseModel):
    """待处理人类输入响应"""
    requests: List[HumanInputRequest]
    total: int

class HumanReviewStats(BaseModel):
    """人类审核统计模型"""
    disputed_count: int
    waiting_human_count: int
    pending_count: int
    recent_pending: List[Dict[str, Any]]  # 最近5条待处理项

def _get_db_engine():
    """获取数据库引擎"""
    return get_db_manager().engine

def create_human_input_request(
    task_id: str,
    title: str,
    description: Optional[str] = None,
    input_type: str = "confirmation",
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    创建一个人类输入请求(辅助函数,用于其他模块调用)
    """
    from sqlalchemy import text

    input_id = f"human-input-{uuid.uuid4().hex[:12]}"

    db_manager = get_db_manager()
    with db_manager.engine.connect() as conn:
        now = datetime.now()
        conn.execute(text("""
            INSERT INTO human_input_requests
            (id, task_id, title, description, input_type, status, context, created_at, updated_at)
            VALUES (:id, :task_id, :title, :description, :input_type, :status, :context, :created_at, :updated_at)
        """), {
            "id": input_id,
            "task_id": task_id,
            "title": title,
            "description": description,
            "input_type": input_type,
            "status": "pending",
            "context": json.dumps(context) if context else None,
            "created_at": now,
            "updated_at": now
        })
        conn.commit()

    return input_id
