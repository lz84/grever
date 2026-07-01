"""
Scenario 项目/任务 CRUD 端点

职责：
- 项目增删改
- 任务增删改
"""

import json
import uuid
from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from reins.common.database import get_db
from models import ScenarioTask, Scenario
from models.scenario import ScenarioProjectModel as ScenarioProject
from .crud import _verify_scenario_exists, _parse_json_field

router = APIRouter(tags=["scenarios"])


class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    project_type: str = 'mandatory'
    condition_type: str = 'none'
    condition_data: Optional[dict] = None
    next_step: Optional[list] = None
    capability_tags: Optional[Union[dict, list[str]]] = None
    order_index: int = 0


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    project_type: Optional[str] = None
    condition_type: Optional[str] = None
    condition_data: Optional[dict] = None
    next_step: Optional[list] = None
    capability_tags: Optional[Union[dict, list[str]]] = None
    order_index: Optional[int] = None


class TaskCreateRequest(BaseModel):
    project_id: str
    phase_name: str
    name: str
    description: Optional[str] = None
    required_capabilities: Optional[list] = None
    dependencies: Optional[list] = None
    order_in_phase: int = 0
    priority: str = 'medium'
    condition_type: str = 'none'
    condition_data: Optional[dict] = None
    executor_type: str = 'ai'


class TaskUpdateRequest(BaseModel):
    phase_name: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    required_capabilities: Optional[list] = None
    dependencies: Optional[list] = None
    order_in_phase: Optional[int] = None
    priority: Optional[str] = None
    condition_type: Optional[str] = None
    condition_data: Optional[dict] = None
    executor_type: Optional[str] = None


@router.post("/{scenario_id}/projects", status_code=201)
def create_scenario_project(scenario_id: str, data: ProjectCreateRequest, db: Session = Depends(get_db)):
    if not _verify_scenario_exists(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")

    order_index = data.order_index
    if order_index is None or order_index == 0:
        max_order = db.query(ScenarioProject).filter(
            ScenarioProject.scenario_id == scenario_id
        ).with_entities(
            ScenarioProject.order_index
        ).order_by(
            ScenarioProject.order_index.desc()
        ).first()
        order_index = (max_order[0] if max_order else -1) + 1

    project = ScenarioProject(
        id=f"sp-{uuid.uuid4().hex[:12]}",
        scenario_id=scenario_id,
        name=data.name,
        description=data.description or "",
        project_type=data.project_type,
        condition_type=data.condition_type,
        condition_data=json.dumps(data.condition_data) if data.condition_data else None,
        next_step=json.dumps(data.next_step) if data.next_step else None,
        capability_tags=json.dumps(data.capability_tags) if data.capability_tags else '{}',
        order_index=order_index,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return {
        "id": project.id,
        "scenario_id": scenario_id,
        "name": project.name,
        "description": project.description,
        "project_type": project.project_type,
        "condition_type": project.condition_type,
        "condition_data": _parse_json_field(project.condition_data),
        "next_step": _parse_json_field(project.next_step),
        "capability_tags": _parse_json_field(project.capability_tags),
        "order_index": project.order_index,
    }


@router.put("/{scenario_id}/projects/{project_id}")
def update_scenario_project(scenario_id: str, project_id: str, data: ProjectUpdateRequest, db: Session = Depends(get_db)):
    if not _verify_scenario_exists(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")

    project = db.query(ScenarioProject).filter(
        ScenarioProject.id == project_id,
        ScenarioProject.scenario_id == scenario_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    if data.project_type is not None:
        project.project_type = data.project_type
    if data.condition_type is not None:
        project.condition_type = data.condition_type
    if data.condition_data is not None:
        project.condition_data = json.dumps(data.condition_data)
    if data.next_step is not None:
        project.next_step = json.dumps(data.next_step)
    if data.capability_tags is not None:
        project.capability_tags = json.dumps(data.capability_tags)
    if data.order_index is not None:
        project.order_index = data.order_index

    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)

    return {
        "id": project.id,
        "scenario_id": scenario_id,
        "name": project.name,
        "description": project.description,
        "project_type": project.project_type,
        "condition_type": project.condition_type,
        "condition_data": _parse_json_field(project.condition_data),
        "next_step": _parse_json_field(project.next_step),
        "capability_tags": _parse_json_field(project.capability_tags),
        "order_index": project.order_index,
    }


@router.delete("/{scenario_id}/projects/{project_id}", status_code=204)
def delete_scenario_project(scenario_id: str, project_id: str, db: Session = Depends(get_db)):
    if not _verify_scenario_exists(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")

    project = db.query(ScenarioProject).filter(
        ScenarioProject.id == project_id,
        ScenarioProject.scenario_id == scenario_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.query(ScenarioTask).filter(ScenarioTask.project_id == project_id).delete()
    db.query(ScenarioProject).filter(ScenarioProject.id == project_id).delete()
    db.commit()


@router.post("/{scenario_id}/tasks", status_code=201)
def create_scenario_task(scenario_id: str, data: TaskCreateRequest, db: Session = Depends(get_db)):
    if not _verify_scenario_exists(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")

    project = db.query(ScenarioProject).filter(
        ScenarioProject.id == data.project_id,
        ScenarioProject.scenario_id == scenario_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {data.project_id} not found in this scenario")

    task = ScenarioTask(
        id=f"st-{uuid.uuid4().hex[:12]}",
        scenario_id=scenario_id,
        project_id=data.project_id,
        phase_name=data.phase_name,
        name=data.name,
        description=data.description or "",
        required_capabilities=json.dumps(data.required_capabilities) if data.required_capabilities else None,
        dependencies=json.dumps(data.dependencies) if data.dependencies else None,
        order_in_phase=data.order_in_phase,
        priority=data.priority,
        condition_type=data.condition_type,
        condition_data=json.dumps(data.condition_data) if data.condition_data else None,
        executor_type=data.executor_type,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "id": task.id,
        "scenario_id": task.scenario_id,
        "project_id": task.project_id,
        "phase_name": task.phase_name,
        "name": task.name,
        "description": task.description,
        "required_capabilities": _parse_json_field(task.required_capabilities),
        "dependencies": _parse_json_field(task.dependencies),
        "order_in_phase": task.order_in_phase,
        "priority": task.priority,
        "condition_type": task.condition_type,
        "condition_data": _parse_json_field(task.condition_data),
        "executor_type": task.executor_type or 'ai',
    }


@router.put("/{scenario_id}/tasks/{task_id}")
def update_scenario_task(scenario_id: str, task_id: str, data: TaskUpdateRequest, db: Session = Depends(get_db)):
    if not _verify_scenario_exists(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")

    task = db.query(ScenarioTask).filter(
        ScenarioTask.id == task_id,
        ScenarioTask.scenario_id == scenario_id,
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if data.phase_name is not None:
        task.phase_name = data.phase_name
    if data.name is not None:
        task.name = data.name
    if data.description is not None:
        task.description = data.description
    if data.order_in_phase is not None:
        task.order_in_phase = data.order_in_phase
    if data.priority is not None:
        task.priority = data.priority
    if data.condition_type is not None:
        task.condition_type = data.condition_type
    if data.executor_type is not None:
        task.executor_type = data.executor_type
    if data.required_capabilities is not None:
        task.required_capabilities = json.dumps(data.required_capabilities)
    if data.dependencies is not None:
        task.dependencies = json.dumps(data.dependencies)
    if data.condition_data is not None:
        task.condition_data = json.dumps(data.condition_data)

    task.updated_at = int(datetime.utcnow().timestamp())
    db.commit()
    db.refresh(task)

    return {
        "id": task.id,
        "scenario_id": task.scenario_id,
        "project_id": task.project_id,
        "phase_name": task.phase_name,
        "name": task.name,
        "description": task.description,
        "required_capabilities": _parse_json_field(task.required_capabilities),
        "dependencies": _parse_json_field(task.dependencies),
        "order_in_phase": task.order_in_phase,
        "priority": task.priority,
        "condition_type": task.condition_type,
        "condition_data": _parse_json_field(task.condition_data),
        "executor_type": task.executor_type or 'ai',
    }


@router.delete("/{scenario_id}/tasks/{task_id}", status_code=204)
def delete_scenario_task(scenario_id: str, task_id: str, db: Session = Depends(get_db)):
    if not _verify_scenario_exists(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")

    task = db.query(ScenarioTask).filter(
        ScenarioTask.id == task_id,
        ScenarioTask.scenario_id == scenario_id,
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()