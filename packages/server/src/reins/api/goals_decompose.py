"""Goals API: decomposition & verifier endpoints."""
from loguru import logger
import traceback

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models.goal import Goal, GoalResponse
from shared.database import get_db
from services.goal_decomposition import decompose_goal as decompose_goal_service, decompose_and_create_tasks
from .goals_models import SetGoalVerifierRequest

router = APIRouter()

@router.post("/{goal_id}/decompose", response_model=GoalResponse)
def decompose_goal(
    goal_id: int,
    auto_create: bool = Query(True, description="是否自动创建任务"),
    db: Session = Depends(get_db),
):
    """分解目标为任务"""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    try:
        if auto_create:
            created_tasks = decompose_and_create_tasks(
                goal_id=goal.id,
                goal_title=goal.title,
                goal_description=goal.description,
                db=db,
            )
            logger.info(f"[Goals API] Created {len(created_tasks)} tasks")
        else:
            tasks = decompose_goal_service(goal.title, goal.description)
            logger.info(f"[Goals API] Decomposed to {len(tasks)} tasks")
        return goal.to_dict()
    except Exception as e:
        logger.info(f"[Goals API] decompose failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"目标分解失败: {str(e)}")

@router.post("/{goal_id}/decompose/preview")
def preview_decomposition(goal_id: int, db: Session = Depends(get_db)):
    """预览目标分解结果"""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    try:
        tasks = decompose_goal_service(goal.title, goal.description)
        return {"goal_id": goal.id, "goal_title": goal.title, "tasks": tasks, "task_count": len(tasks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"目标分解失败: {str(e)}")

@router.post("/{goal_id}/verifier")
def set_goal_verifier(goal_id: str, request: SetGoalVerifierRequest, db: Session = Depends(get_db)):
    """设置 Goal 的验证 Agent ID"""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal.verifier_agent_id = request.verifier_agent_id
    goal.updated_at = __import__('datetime').datetime.now()
    db.commit()
    db.refresh(goal)

    return {"goal_id": goal_id, "verifier_agent_id": request.verifier_agent_id}
