"""
Scenario 项目/任务 CRUD 端点

职责：
- 项目增删改
- 任务增删改
"""

import json
import uuid
from typing import Optional, Union

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from reins.common.database import get_db

# Import helpers from crud
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
    agent_type: Optional[str] = None
    required_capabilities: Optional[list] = None
    dependencies: Optional[list] = None
    order_in_phase: int = 0
    estimated_hours: Optional[float] = None
    priority: str = 'medium'
    condition_type: str = 'none'
    condition_data: Optional[dict] = None
    executor_type: str = 'ai'


class TaskUpdateRequest(BaseModel):
    phase_name: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    agent_type: Optional[str] = None
    required_capabilities: Optional[list] = None
    dependencies: Optional[list] = None
    order_in_phase: Optional[int] = None
    estimated_hours: Optional[float] = None
    priority: Optional[str] = None
    condition_type: Optional[str] = None
    condition_data: Optional[dict] = None
    executor_type: Optional[str] = None


def _project_row_to_dict(row):
    return {
        "id": row[0], "scenario_id": None, "name": row[1], "description": row[2],
        "project_type": row[3], "condition_type": row[4],
        "condition_data": _parse_json_field(row[5]),
        "next_step": _parse_json_field(row[6]),
        "capability_tags": _parse_json_field(row[7]), "order_index": row[8],
    }


@router.post("/{scenario_id}/projects", status_code=201)
def create_scenario_project(scenario_id: str, data: ProjectCreateRequest, db: Session = Depends(get_db)):
    if not _verify_scenario_exists(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")
    project_id = f"sp-{uuid.uuid4().hex[:12]}"
    order_index = data.order_index
    if order_index is None:
        row = db.execute(
            text("SELECT COALESCE(MAX(order_index), -1) FROM scenario_projects WHERE scenario_id = :sid"),
            {"sid": scenario_id},
        ).fetchone()
        order_index = (row[0] if row else -1) + 1
    db.execute(text("""
        INSERT INTO scenario_projects (id, scenario_id, name, description, project_type, condition_type,
             condition_data, next_step, capability_tags, order_index)
        VALUES (:id, :sid, :name, :desc, :ptype, :ctype, :cdata, :nstep, :ctags, :oindex)
    """), {
        "id": project_id, "sid": scenario_id, "name": data.name, "desc": data.description or "",
        "ptype": data.project_type, "ctype": data.condition_type,
        "cdata": json.dumps(data.condition_data) if data.condition_data else None,
        "nstep": json.dumps(data.next_step) if data.next_step else None,
        "ctags": json.dumps(data.capability_tags) if data.capability_tags else '{}',
        "oindex": order_index,
    })
    db.commit()
    row = db.execute(text(
        "SELECT id, name, description, project_type, condition_type, condition_data, next_step, capability_tags, order_index "
        "FROM scenario_projects WHERE id = :id"
    ), {"id": project_id}).fetchone()
    result = _project_row_to_dict(row)
    result["scenario_id"] = scenario_id
    return result


@router.put("/{scenario_id}/projects/{project_id}")
def update_scenario_project(scenario_id: str, project_id: str, data: ProjectUpdateRequest, db: Session = Depends(get_db)):
    if not _verify_scenario_exists(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")
    row = db.execute(
        text("SELECT id FROM scenario_projects WHERE id = :pid AND scenario_id = :sid"),
        {"pid": project_id, "sid": scenario_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    updates, params = [], {"pid": project_id}
    for field, value in [('name', data.name), ('description', data.description),
                          ('project_type', data.project_type), ('condition_type', data.condition_type)]:
        if value is not None:
            updates.append(f"{field} = :{field}")
            params[field] = value
    for json_field, value in [('condition_data', data.condition_data),
                               ('next_step', data.next_step), ('capability_tags', data.capability_tags)]:
        if value is not None:
            updates.append(f"{json_field} = :{json_field}")
            params[json_field] = json.dumps(value)
    if data.order_index is not None:
        updates.append("order_index = :oindex")
        params["oindex"] = data.order_index
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates.append("updated_at = CURRENT_TIMESTAMP")
    db.execute(text(f"UPDATE scenario_projects SET {', '.join(updates)} WHERE id = :pid"), params)
    db.commit()
    row = db.execute(text(
        "SELECT id, name, description, project_type, condition_type, condition_data, next_step, capability_tags, order_index "
        "FROM scenario_projects WHERE id = :id"
    ), {"id": project_id}).fetchone()
    result = _project_row_to_dict(row)
    result["scenario_id"] = scenario_id
    return result


@router.delete("/{scenario_id}/projects/{project_id}", status_code=204)
def delete_scenario_project(scenario_id: str, project_id: str, db: Session = Depends(get_db)):
    if not _verify_scenario_exists(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")
    row = db.execute(
        text("SELECT id FROM scenario_projects WHERE id = :pid AND scenario_id = :sid"),
        {"pid": project_id, "sid": scenario_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    db.execute(text("DELETE FROM scenario_tasks WHERE project_id = :pid"), {"pid": project_id})
    db.execute(text("DELETE FROM scenario_projects WHERE id = :pid"), {"pid": project_id})
    db.commit()


@router.post("/{scenario_id}/tasks", status_code=201)
def create_scenario_task(scenario_id: str, data: TaskCreateRequest, db: Session = Depends(get_db)):
    if not _verify_scenario_exists(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")
    row = db.execute(
        text("SELECT id FROM scenario_projects WHERE id = :pid AND scenario_id = :sid"),
        {"pid": data.project_id, "sid": scenario_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Project {data.project_id} not found in this scenario")
    task_id = f"st-{uuid.uuid4().hex[:12]}"
    db.execute(text("""
        INSERT INTO scenario_tasks (id, scenario_id, project_id, phase_name, name, description, agent_type,
             required_capabilities, dependencies, order_in_phase, estimated_hours, priority, condition_type, condition_data, executor_type)
        VALUES (:id, :sid, :pid, :phase, :name, :desc, :agent, :rcaps, :deps, :oip, :ehours, :priority, :ctype, :cdata, :executor_type)
    """), {
        "id": task_id, "sid": scenario_id, "pid": data.project_id, "phase": data.phase_name,
        "name": data.name, "desc": data.description or "", "agent": data.agent_type,
        "rcaps": json.dumps(data.required_capabilities) if data.required_capabilities else None,
        "deps": json.dumps(data.dependencies) if data.dependencies else None,
        "oip": data.order_in_phase, "ehours": data.estimated_hours, "priority": data.priority,
        "ctype": data.condition_type,
        "cdata": json.dumps(data.condition_data) if data.condition_data else None,
        "executor_type": data.executor_type,
    })
    db.commit()
    row = db.execute(text(
        "SELECT id, scenario_id, project_id, phase_name, name, description, agent_type, "
        "required_capabilities, dependencies, order_in_phase, estimated_hours, priority, "
        "condition_type, condition_data, executor_type FROM scenario_tasks WHERE id = :id"
    ), {"id": task_id}).fetchone()
    return {
        "id": row[0], "scenario_id": row[1], "project_id": row[2], "phase_name": row[3],
        "name": row[4], "description": row[5], "agent_type": row[6],
        "required_capabilities": _parse_json_field(row[7]), "dependencies": _parse_json_field(row[8]),
        "order_in_phase": row[9], "estimated_hours": row[10], "priority": row[11],
        "condition_type": row[12], "condition_data": _parse_json_field(row[13]),
        "executor_type": row[14] if len(row) > 14 else 'ai',
    }


@router.put("/{scenario_id}/tasks/{task_id}")
def update_scenario_task(scenario_id: str, task_id: str, data: TaskUpdateRequest, db: Session = Depends(get_db)):
    if not _verify_scenario_exists(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")
    row = db.execute(
        text("SELECT id FROM scenario_tasks WHERE id = :tid AND scenario_id = :sid"),
        {"tid": task_id, "sid": scenario_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    updates, params = [], {"tid": task_id}
    for field, value in [('phase_name', data.phase_name), ('name', data.name),
                          ('description', data.description), ('agent_type', data.agent_type),
                          ('order_in_phase', data.order_in_phase), ('estimated_hours', data.estimated_hours),
                          ('priority', data.priority), ('condition_type', data.condition_type),
                          ('executor_type', data.executor_type)]:
        if value is not None:
            updates.append(f"{field} = :{field}")
            params[field] = value
    for json_field, value in [('required_capabilities', data.required_capabilities),
                               ('dependencies', data.dependencies), ('condition_data', data.condition_data)]:
        if value is not None:
            updates.append(f"{json_field} = :{json_field}")
            params[json_field] = json.dumps(value)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates.append("updated_at = CURRENT_TIMESTAMP")
    db.execute(text(f"UPDATE scenario_tasks SET {', '.join(updates)} WHERE id = :tid"), params)
    db.commit()
    row = db.execute(text(
        "SELECT id, scenario_id, project_id, phase_name, name, description, agent_type, "
        "required_capabilities, dependencies, order_in_phase, estimated_hours, priority, "
        "condition_type, condition_data, executor_type FROM scenario_tasks WHERE id = :id"
    ), {"id": task_id}).fetchone()
    return {
        "id": row[0], "scenario_id": row[1], "project_id": row[2], "phase_name": row[3],
        "name": row[4], "description": row[5], "agent_type": row[6],
        "required_capabilities": _parse_json_field(row[7]), "dependencies": _parse_json_field(row[8]),
        "order_in_phase": row[9], "estimated_hours": row[10], "priority": row[11],
        "condition_type": row[12], "condition_data": _parse_json_field(row[13]),
        "executor_type": row[14] if len(row) > 14 else 'ai',
    }


@router.delete("/{scenario_id}/tasks/{task_id}", status_code=204)
def delete_scenario_task(scenario_id: str, task_id: str, db: Session = Depends(get_db)):
    if not _verify_scenario_exists(db, scenario_id):
        raise HTTPException(status_code=404, detail="Scenario not found")
    row = db.execute(
        text("SELECT id FROM scenario_tasks WHERE id = :tid AND scenario_id = :sid"),
        {"tid": task_id, "sid": scenario_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    db.execute(text("DELETE FROM scenario_tasks WHERE id = :tid"), {"tid": task_id})
    db.commit()
