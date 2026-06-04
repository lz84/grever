"""Task context endpoint (MAK-214) — split from assignment_endpoints.py"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from reins.common.database import get_db

router = APIRouter()

@router.get("/tasks/{task_id}/context")
def get_task_context_endpoint(task_id: str, db: Session = Depends(get_db)):
    """获取任务上下文信息（MAK-214）"""
    from reins.api.assignment_services import get_task_context as _get_ctx
    context = _get_ctx(task_id, db)
    if not context:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "task_id": task_id, "context": context}
