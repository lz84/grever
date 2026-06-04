"""Task CRUD — Delete endpoint (delete_task)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.task import Task
from reins.common.database import get_db
from reins.api.tasks_crud_helpers import _cleanup_all_on_delete

router = APIRouter(tags=["tasks"])


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """Delete Task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    _cleanup_all_on_delete(task, db)
    # Use raw SQL to delete task to avoid ORM cascade issues (e.g. HumanInputRequest schema_json column mismatch)
    db.execute(text("DELETE FROM tasks WHERE id = :tid"), {"tid": task_id})
    db.commit()
    return
