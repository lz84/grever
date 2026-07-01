"""
API endpoints for Git workspace operations.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from loguru import logger
from ..database import get_db
from ..models.goal import Goal
from ..services.workspace_manager import (
    clone_workspace, 
    pull_workspace, 
    push_workspace, 
    get_workspace_status
)

router = APIRouter(prefix="/api/v1/goals", tags=["workspace"])

@router.post("/{goal_id}/workspace/clone")
def clone_workspace_endpoint(goal_id: str, db: Session = Depends(get_db)):
    """
    Clone a Git repository for the specified goal.
    Returns 400 if workspace_type is not 'git'.
    """
    # Find the goal
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="目标不存在")
    
    # Check if workspace_type is 'git'
    if goal.workspace_type != 'git':
        raise HTTPException(status_code=400, detail="目标的 workspace_type 不是 'git'")
    
    # Update status to indicate we're starting clone
    goal.workspace_status = 'pending'
    goal.workspace_error = None
    db.commit()
    
    # Perform the clone operation
    result = clone_workspace(goal.workspace_path, goal_id)
    
    # Update the goal record based on the result
    if result['success']:
        goal.workspace_status = 'cloned'
        goal.last_clone_at = datetime.now()
        goal.workspace_error = None
    else:
        goal.workspace_status = 'error'
        goal.workspace_error = result['error']
    
    db.commit()
    
    return result

@router.post("/{goal_id}/workspace/pull")
def pull_workspace_endpoint(goal_id: str, db: Session = Depends(get_db)):
    """
    Pull latest changes from the Git repository for the specified goal.
    """
    # Find the goal
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="目标不存在")
    
    # Check if workspace_type is 'git'
    if goal.workspace_type != 'git':
        raise HTTPException(status_code=400, detail="目标的 workspace_type 不是 'git'")
    
    # Update status to indicate we're starting pull
    goal.workspace_status = 'pulling'
    db.commit()
    
    # Perform the pull operation
    result = pull_workspace(goal_id)
    
    # Update the goal record based on the result
    if result['success']:
        goal.workspace_status = 'cloned'
        goal.last_pull_at = datetime.now()
        goal.workspace_error = None
    else:
        goal.workspace_status = 'pulling_failed'
        goal.workspace_error = result['error']
    
    db.commit()
    
    return result

@router.post("/{goal_id}/workspace/push")
def push_workspace_endpoint(goal_id: str, commit_msg: str = "Auto-commit from Grever", db: Session = Depends(get_db)):
    """
    Push changes to the Git repository for the specified goal.
    """
    # Find the goal
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="目标不存在")
    
    # Check if workspace_type is 'git'
    if goal.workspace_type != 'git':
        raise HTTPException(status_code=400, detail="目标的 workspace_type 不是 'git'")
    
    # Perform the push operation
    result = push_workspace(goal_id, commit_msg)
    
    # Update the goal record based on the result
    if result['success']:
        goal.workspace_status = 'cloned'
        goal.last_push_at = datetime.now()
        goal.workspace_error = None
    else:
        goal.workspace_status = 'pushing_failed'
        goal.workspace_error = result['error']
    
    db.commit()
    
    return result

@router.get("/{goal_id}/workspace/status")
def workspace_status_endpoint(goal_id: str, db: Session = Depends(get_db)):
    """
    Get the workspace status for the specified goal.
    """
    # Find the goal
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="目标不存在")
    
    # Check if workspace_type is 'git'
    if goal.workspace_type != 'git':
        raise HTTPException(status_code=400, detail="目标的 workspace_type 不是 'git'")
    
    # Get workspace status
    status = get_workspace_status(goal_id)
    
    # Return combined information
    return {
        "goal_workspace_status": goal.workspace_status,
        "goal_workspace_error": goal.workspace_error,
        "last_clone_at": goal.last_clone_at.isoformat() if goal.last_clone_at else None,
        "last_pull_at": goal.last_pull_at.isoformat() if goal.last_pull_at else None,
        "last_push_at": goal.last_push_at.isoformat() if goal.last_push_at else None,
        **status
    }