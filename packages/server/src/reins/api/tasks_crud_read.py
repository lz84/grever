"""Task CRUD — Read endpoint (get_task)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.task import Task, TaskResponse
from reins.common.database import get_db

router = APIRouter(tags=["tasks"])


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    """Get single task by ID"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task.to_dict()
