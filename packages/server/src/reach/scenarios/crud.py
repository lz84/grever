"""
Scenario CRUD — 公共 helpers + 场景写端点

职责：
1. CRUD helpers（count, build, create, update, parse）
2. 写端点：create, update, delete, status, review

项目/任务 CRUD 已移至 projects.py
"""

import json
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from reins.common.database import get_db
from models import ScenarioTask, Scenario
from models.scenario import (
    ScenarioProjectModel as ScenarioProject,
    ScenarioProject as _ScenarioProject,
    ScenarioMetrics, ScenarioCreate, ScenarioUpdate, ScenarioResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["scenarios"])


# === Helpers ===

def _count_projects(db: Session, scenario_id: str) -> int:
    return db.query(ScenarioProject).filter(
        ScenarioProject.scenario_id == scenario_id
    ).count()


def _build_projects_array(db: Session, scenario_id: str) -> List[_ScenarioProject]:
    projects = db.query(ScenarioProject).filter(
        ScenarioProject.scenario_id == scenario_id
    ).order_by(ScenarioProject.order_index).all()

    tasks = db.query(ScenarioTask).filter(
        ScenarioTask.scenario_id == scenario_id,
        ScenarioTask.project_id.isnot(None),
    ).all()

    tasks_by_project: Dict[str, list] = {}
    for task in tasks:
        pid = task.project_id
        if pid:
            t = {
                "id": task.id,
                "name": task.name or '',
                "description": task.description,
                "required_capabilities": task.required_capabilities,
                "dependencies": task.dependencies,
                "order_in_phase": task.order_in_phase,
                "priority": task.priority,
                "condition_type": task.condition_type or 'none',
                "condition_data": task.condition_data,
                "executor_type": task.executor_type or 'ai',
            }
            tasks_by_project.setdefault(pid, []).append(t)

    result = []
    for proj in projects:
        project = _ScenarioProject(
            id=proj.id, name=proj.name,
            description=proj.description,
            order=proj.order_index, agent_type=None, required_capabilities=None,
            condition_type=proj.condition_type or 'none',
            condition_data=proj.condition_data,
            project_type=proj.project_type or 'mandatory',
            capability_tags=proj.capability_tags,
            next_step=proj.next_step,
            tasks=tasks_by_project.get(proj.id, []),
        )
        result.append(project)
    return result


def _parse_json_field(value):
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def _verify_scenario_exists(db: Session, scenario_id: str) -> bool:
    row = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    return row is not None


def _build_scenario_response(db: Session, scenario: Scenario) -> ScenarioResponse:
    total_executions = scenario.total_executions or 0
    success_count = scenario.success_count or 0
    success_rate = (success_count / total_executions * 100) if total_executions > 0 else 0
    metrics = ScenarioMetrics(
        total_executions=total_executions, success_count=success_count,
        failed_count=scenario.failed_count or 0, success_rate=success_rate,
        avg_duration_ms=scenario.avg_duration_ms or 0,
        min_duration_ms=scenario.min_duration_ms or 0,
        max_duration_ms=scenario.max_duration_ms or 0,
        avg_conflicts=scenario.avg_conflicts or 0,
        avg_step_completion=scenario.avg_step_completion or 0,
    )
    steps = []
    versions_data = scenario.versions or []
    if isinstance(versions_data, str):
        try:
            versions_data = json.loads(versions_data)
        except Exception:
            versions_data = []

    projects = _build_projects_array(db, scenario.id)

    task_templates = db.query(ScenarioTask).filter(
        ScenarioTask.scenario_id == scenario.id
    ).all()
    task_templates_list = []
    for t in task_templates:
        task_templates_list.append({
            "id": t.id, "phase_name": t.phase_name, "name": t.name, "description": t.description,
            "required_capabilities": t.required_capabilities,
            "dependencies": t.dependencies,
            "order_in_phase": t.order_in_phase,
            "priority": t.priority,
            "condition_type": t.condition_type or 'none',
            "condition_data": t.condition_data,
            "executor_type": t.executor_type or 'ai',
        })

    fullset_data = scenario.fullset
    if isinstance(fullset_data, str):
        try:
            fullset_data = json.loads(fullset_data)
        except Exception:
            fullset_data = None

    gct_data = getattr(scenario, 'goal_capability_tags', None)
    if isinstance(gct_data, str):
        try:
            gct_data = json.loads(gct_data)
        except Exception:
            gct_data = None

    return ScenarioResponse(
        id=scenario.id, name=scenario.name, category=scenario.category,
        status=scenario.status, version=scenario.version,
        level=getattr(scenario, 'level', None),
        trust_level=getattr(scenario, 'trust_level', None),
        source=getattr(scenario, 'source', None),
        description=scenario.description,
        scenario_desc=scenario.scenario_desc or "",
        triggers=scenario.triggers or [], steps=steps, metrics=metrics,
        versions=versions_data if isinstance(versions_data, list) else [],
        template_dag=json.loads(scenario.template_dag) if scenario.template_dag and isinstance(scenario.template_dag, str) else (scenario.template_dag or None),
        agent_requirements=json.loads(scenario.agent_requirements) if scenario.agent_requirements and isinstance(scenario.agent_requirements, str) else (scenario.agent_requirements or None),
        task_templates=task_templates_list, projects=projects, fullset=fullset_data,
        goal_capability_tags=gct_data,
        created_at=scenario.created_at.isoformat() if hasattr(scenario.created_at, 'isoformat') and scenario.created_at else str(scenario.created_at) if scenario.created_at else None,
        updated_at=scenario.updated_at.isoformat() if hasattr(scenario.updated_at, 'isoformat') and scenario.updated_at else str(scenario.updated_at) if scenario.updated_at else None,
    )


def _create_scenario_with_projects(db: Session, data: dict) -> Scenario:
    scenario_data = {k: v for k, v in data.items()
                     if k not in ('projects', 'steps', 'task_templates', 'goal_capability_tags')}
    scenario_data.setdefault('triggers', [])
    scenario_data.setdefault('versions', [])
    scenario_data.setdefault('fullset', {})

    projects_data = data.get('projects', [])
    steps_data = data.get('steps', [])

    db_scenario = Scenario(**scenario_data)
    db.add(db_scenario)
    db.flush()

    if projects_data:
        for idx, proj in enumerate(projects_data):
            sp_id = proj.get('id') or f"sp-{uuid.uuid4().hex[:12]}"
            proj_type = proj.get('project_type', proj.get('type', 'mandatory'))
            sp = ScenarioProject(
                id=sp_id,
                scenario_id=db_scenario.id,
                name=proj.get('name', ''),
                description=proj.get('description', ''),
                project_type=proj_type,
                condition_type=proj.get('condition_type', 'none'),
                condition_data=json.dumps(proj.get('condition_data')) if proj.get('condition_data') else None,
                next_step=json.dumps(proj.get('next_step')) if proj.get('next_step') else None,
                capability_tags=json.dumps(proj.get('capability_tags', {})) if proj.get('capability_tags') else '{}',
                order_index=idx,
            )
            db.add(sp)
            for tidx, task in enumerate(proj.get('tasks', [])):
                task_id = task.get('id') or f"task-{uuid.uuid4().hex[:12]}"
                st = ScenarioTask(
                    id=task_id,
                    scenario_id=db_scenario.id,
                    project_id=sp_id,
                    phase_name=proj.get('name', ''),
                    name=task.get('name', ''),
                    description=task.get('description', ''),
                    required_capabilities=json.dumps(task.get('required_capabilities', [])) if task.get('required_capabilities') else None,
                    dependencies=json.dumps(task.get('dependencies', [])) if task.get('dependencies') else None,
                    order_in_phase=task.get('order_in_phase', tidx),
                    priority=task.get('priority', 'medium'),
                    condition_type=task.get('condition_type', 'none'),
                    condition_data=json.dumps(task.get('condition_data')) if task.get('condition_data') else None,
                    executor_type=task.get('executor_type', 'ai'),
                )
                db.add(st)
    elif steps_data:
        for idx, step in enumerate(steps_data):
            sp_id = step.get('id') or f"sp-{uuid.uuid4().hex[:12]}"
            sp = ScenarioProject(
                id=sp_id,
                scenario_id=db_scenario.id,
                name=step.get('name', ''),
                description='',
                order_index=step.get('order', idx),
            )
            db.add(sp)

    db.commit()
    db.refresh(db_scenario)
    return db_scenario


def _update_scenario_with_projects(db: Session, scenario: Scenario, data: dict) -> Scenario:
    projects_data = data.get('projects')
    if projects_data is not None:
        # Delete existing tasks and projects
        db.query(ScenarioTask).filter(ScenarioTask.scenario_id == scenario.id).delete()
        db.query(ScenarioProject).filter(ScenarioProject.scenario_id == scenario.id).delete()

        for idx, proj in enumerate(projects_data):
            sp_id = proj.get('id') or f"sp-{uuid.uuid4().hex[:12]}"
            proj_type = proj.get('project_type', proj.get('type', 'mandatory'))
            sp = ScenarioProject(
                id=sp_id,
                scenario_id=scenario.id,
                name=proj.get('name', ''),
                description=proj.get('description', ''),
                project_type=proj_type,
                condition_type=proj.get('condition_type', 'none'),
                condition_data=json.dumps(proj.get('condition_data')) if proj.get('condition_data') else None,
                next_step=json.dumps(proj.get('next_step')) if proj.get('next_step') else None,
                capability_tags=json.dumps(proj.get('capability_tags', {})) if proj.get('capability_tags') else '{}',
                order_index=idx,
            )
            db.add(sp)
            for tidx, task in enumerate(proj.get('tasks', [])):
                task_id = task.get('id') or f"task-{uuid.uuid4().hex[:12]}"
                st = ScenarioTask(
                    id=task_id,
                    scenario_id=scenario.id,
                    project_id=sp_id,
                    phase_name=proj.get('name', ''),
                    name=task.get('name', ''),
                    description=task.get('description', ''),
                    required_capabilities=json.dumps(task.get('required_capabilities', [])) if task.get('required_capabilities') else None,
                    dependencies=json.dumps(task.get('dependencies', [])) if task.get('dependencies') else None,
                    order_in_phase=task.get('order_in_phase', tidx),
                    priority=task.get('priority', 'medium'),
                    condition_type=task.get('condition_type', 'none'),
                    condition_data=json.dumps(task.get('condition_data')) if task.get('condition_data') else None,
                    executor_type=task.get('executor_type', 'ai'),
                )
                db.add(st)

    for key, value in data.items():
        if key not in ('projects', 'steps', 'task_templates', 'goal_capability_tags') and value is not None:
            setattr(scenario, key, value)
    scenario.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(scenario)
    return scenario


# === Scenario Write Endpoints ===

@router.patch("/{scenario_id}/status")
def update_scenario_status(scenario_id: str, body: Dict[str, str] = Body(...), db: Session = Depends(get_db)):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    scenario.status = body.get("status", scenario.status)
    scenario.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(scenario)
    return _build_scenario_response(db, scenario)


@router.post("/{scenario_id}/review")
def review_scenario(scenario_id: str, body: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    action = body.get("action")
    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
    if scenario.status != "review_needed":
        raise HTTPException(status_code=400, detail="Only 'review_needed' scenarios can be reviewed")
    if action == "approve":
        scenario.status = "active"
    elif action == "reject":
        scenario.status = "draft"
    scenario.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(scenario)
    return {"success": True, "message": f"Scenario {action}d", "scenario_id": scenario.id, "new_status": scenario.status}


@router.post("/", status_code=201)
def create_scenario(scenario_data: ScenarioCreate, db: Session = Depends(get_db)):
    try:
        data = scenario_data.model_dump()
        db_scenario = _create_scenario_with_projects(db, data)
        return _build_scenario_response(db, db_scenario)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建场景失败: {str(e)}")


@router.put("/{scenario_id}")
def update_scenario(scenario_id: str, scenario_data: ScenarioUpdate, db: Session = Depends(get_db)):
    try:
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        data = scenario_data.model_dump(exclude_unset=True)
        _update_scenario_with_projects(db, scenario, data)
        return _build_scenario_response(db, scenario)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新场景失败: {str(e)}")


@router.delete("/{scenario_id}", status_code=204)
def delete_scenario(scenario_id: str, db: Session = Depends(get_db)):
    try:
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        db.query(ScenarioTask).filter(ScenarioTask.scenario_id == scenario_id).delete()
        db.query(ScenarioProject).filter(ScenarioProject.scenario_id == scenario_id).delete()
        db.delete(scenario)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除场景失败: {str(e)}")
