"""Task labels CRUD endpoints."""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.additional_models import TaskLabel
from models.task import Task
from reins.common.database import get_db

router = APIRouter()


@router.get("/labels/all")
def get_all_labels(db: Session = Depends(get_db)):
    """Get all unique label names across all tasks."""
    labels = db.query(TaskLabel.name).distinct().all()
    return [row[0] for row in labels]


@router.get("/{task_id}/labels")
def get_task_labels(task_id: str, db: Session = Depends(get_db)):
    """Get labels for a specific task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    labels = db.query(TaskLabel).filter(TaskLabel.task_id == task_id).all()
    return [label.name for label in labels]


@router.post("/{task_id}/labels")
def add_label(task_id: str, request: dict, db: Session = Depends(get_db)):
    """Add a label to a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    label_name = request.get("label", "").strip()
    if not label_name:
        raise HTTPException(status_code=400, detail="Label name is required")

    # Check if label already exists for this task
    existing = db.query(TaskLabel).filter(
        TaskLabel.task_id == task_id,
        TaskLabel.name == label_name,
    ).first()
    if existing:
        return {"success": True}

    new_label = TaskLabel(
        id=str(uuid.uuid4()),
        task_id=task_id,
        name=label_name,
        color=request.get("color") or "",
        created_at=datetime.utcnow(),
    )
    db.add(new_label)
    db.commit()
    return {"success": True}


@router.delete("/{task_id}/labels/{label_id}")
def delete_label(task_id: str, label_id: str, db: Session = Depends(get_db)):
    """Delete a label from a task."""
    label = db.query(TaskLabel).filter(
        TaskLabel.id == label_id,
        TaskLabel.task_id == task_id,
    ).first()
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")
    db.delete(label)
    db.commit()
    return {"success": True}
