"""Goals API: single-goal CRUD endpoints."""
import json
from loguru import logger
import os
import errno
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Any

from models.goal import Goal, GoalUpdate, GoalResponse
from models.project import Project
from shared.database import get_db, get_db_manager

router = APIRouter(prefix="/api/v1/goals")

@router.get("/{goal_id}", response_model=GoalResponse)
def get_goal(goal_id: str, db: Session = Depends(get_db)):
    """获取单个 Goal"""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal.to_dict()

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_goal(request_data: Any = Body(None), db: Session = Depends(get_db)):
    """创建 Goal"""
    if request_data is None:
        request_data = {}

    now = datetime.now()

    workspace_type = request_data.get("workspace_type")
    workspace_path = request_data.get("workspace_path")

    # 检查/创建工作目录（仅本地路径）
    if workspace_type == "local" and workspace_path:
        try:
            os.path.normpath(workspace_path)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="工作目录路径格式无效，请检查路径名称"
            )

        if os.path.exists(workspace_path):
            if not os.path.isdir(workspace_path):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"路径「{workspace_path}」已存在，但它是一个文件而非目录。请换一个路径，或删除该文件后重试。"
                )
        else:
            try:
                os.makedirs(workspace_path, exist_ok=True)
            except PermissionError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"没有权限创建工作目录「{workspace_path}」。请选择一个你有写入权限的路径。"
                )
            except OSError as e:
                if e.winerror == errno.EINVAL:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"路径「{workspace_path}」包含无效字符或格式不正确。路径不能包含 < > : \" | ? * 等字符。"
                    )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无法创建工作目录「{workspace_path}」：{str(e)}"
                )

    goal = Goal(
        title=request_data.get("title", ""),
        description=request_data.get("description"),
        priority=request_data.get("priority", "medium"),
        due_date=request_data.get("due_date"),
        status=request_data.get("status", "draft"),
        created_at=now,
        updated_at=now,
        progress=0.0,
        workspace_type=workspace_type,
        workspace_path=workspace_path,
        capability_tags=request_data.get("capability_tags"),
        main_agent_id=request_data.get("main_agent_id"),
    )

    # Set scenario_id if provided (for later instantiation)
    scenario_id = request_data.get("scenario_id")
    if scenario_id and hasattr(goal, 'matched_scenario_id'):
        goal.matched_scenario_id = scenario_id

    db.add(goal)
    db.commit()
    db.refresh(goal)

    # Scenario instantiation: if scenario_id is provided, instantiate Projects + Tasks
    instantiation_result = None
    if scenario_id:
        try:
            from .scenario_instantiate import instantiate_scenario
            db_manager = get_db_manager()
            instantiation_result = instantiate_scenario(goal.id, scenario_id, db_manager)
            logger.info(f"[Goal] Instantiated scenario {scenario_id} for goal {goal.id}: {instantiation_result}")
        except Exception as e:
            logger.error(f"[Goal] Failed to instantiate scenario {scenario_id} for goal {goal.id}: {e}")
            # Don't fail goal creation if instantiation fails
            instantiation_result = {"error": str(e), "projects_created": 0, "tasks_created": 0}

    def _serialize_dt(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value) if value else None

    response = {
        "id": goal.id,
        "title": goal.title,
        "description": goal.description,
        "priority": goal.priority,
        "due_date": str(goal.due_date) if goal.due_date else None,
        "status": goal.status,
        "progress": float(goal.progress) if goal.progress else 0.0,
        "created_at": _serialize_dt(goal.created_at),
        "updated_at": _serialize_dt(goal.updated_at),
        "completed_at": None,
        "failed_at": None,
        "goal_id": None,
        "parent_id": None,
        "matched_scenario_id": getattr(goal, 'matched_scenario_id', None),
        "workflow_id": getattr(goal, 'workflow_id', None),
        "workspace_type": getattr(goal, 'workspace_type', None),
        "workspace_path": getattr(goal, 'workspace_path', None),
    }
    if instantiation_result:
        response["instantiation"] = instantiation_result
    return response

@router.put("/{goal_id}", response_model=GoalResponse)
def update_goal(goal_id: str, goal_data: GoalUpdate, db: Session = Depends(get_db)):
    """更新 Goal（支持 Sprint 22 新增字段）"""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    for key, value in goal_data.dict(exclude_unset=True).items():
        if key == 'capability_tags' and value is not None:
            # Ensure capability_tags is stored as JSON string
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif isinstance(value, str):
                # Validate it's valid JSON
                try:
                    json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    value = json.dumps({"raw": value})
        setattr(goal, key, value)
    goal.updated_at = datetime.now()
    db.commit()
    db.refresh(goal)
    return goal.to_dict()

@router.patch("/{goal_id}/status")
def update_goal_status(
    goal_id: str,
    status: str = Query(..., description="目标状态"),
    db: Session = Depends(get_db)
):
    """
    快速更新 Goal 状态（用于前端状态同步按钮）。

    ⚠️ 已废弃：使用 POST /goals/{id}/activate, /pause, /resume 代替。
    新端点具有级联逻辑，此端点仅做简单状态更新。
    """
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # 通过状态机更新状态
    from reins.scheduler.statemachine import GoalStateMachine
    fsm = GoalStateMachine(db, goal_id)
    if not fsm.transition(status, reason="API status update", extra={"updated_at": int(datetime.now().timestamp())}):
        raise HTTPException(status_code=400, detail=f"Invalid status transition: {goal.status} → {status}")
    
    return goal.to_dict()

@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: str, db: Session = Depends(get_db)):
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.execute(text("""
        DELETE FROM tasks WHERE project_id IN (
            SELECT id FROM projects WHERE goal_id = :gid
        )
    """), {"gid": goal_id})
    db.query(Project).filter(Project.goal_id == goal_id).delete()
    db.delete(goal)
    db.commit()
    return
