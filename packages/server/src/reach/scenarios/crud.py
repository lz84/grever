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
from sqlalchemy import text
from sqlalchemy.orm import Session

from reins.common.database import get_db
from models.scenario import (
    Scenario, ScenarioProject, ScenarioProjectTask,
    ScenarioMetrics, ScenarioCreate, ScenarioUpdate, ScenarioResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["scenarios"])


# === Helpers ===

def _count_projects(db: Session, scenario_id: str) -> int:
    row = db.execute(
        text("SELECT COUNT(*) FROM scenario_projects WHERE scenario_id = :sid"),
        {"sid": scenario_id},
    ).fetchone()
    return row[0] if row else 0


def _build_projects_array(db: Session, scenario_id: str) -> List[ScenarioProject]:
    projects_result = db.execute(text("""
        SELECT sp.id, sp.scenario_id, sp.name, sp.description, sp.order_index, sp.project_type,
               sp.condition_type, sp.condition_data, sp.capability_tags, sp.next_step
        FROM scenario_projects sp WHERE sp.scenario_id = :scenario_id ORDER BY sp.order_index
    """), {"scenario_id": scenario_id})

    tasks_result = db.execute(text("""
        SELECT id, phase_name, name, description, agent_type,
               required_capabilities, dependencies, order_in_phase,
               estimated_hours, priority, condition_type, condition_data, project_id, executor_type
        FROM scenario_tasks
        WHERE scenario_id = :scenario_id AND project_id IS NOT NULL
    """), {"scenario_id": scenario_id})

    tasks_by_project: Dict[str, list] = {}
    for row in tasks_result:
        pid = row[12]
        if pid:
            task = ScenarioProjectTask(
                id=row[0], name=row[2], description=row[3], agent_type=row[4],
                required_capabilities=row[5], dependencies=row[6], order_in_phase=row[7],
                estimated_hours=row[8], priority=row[9],
                condition_type=row[10] if len(row) > 10 else 'none',
                condition_data=row[11] if len(row) > 11 else None,
                executor_type=row[13] if len(row) > 13 else 'ai',
            )
            tasks_by_project.setdefault(pid, []).append(task)

    projects = []
    for proj_row in projects_result:
        project = ScenarioProject(
            id=proj_row[0], name=proj_row[2],
            description=proj_row[3] if len(proj_row) > 3 else None,
            order=proj_row[4], agent_type=None, required_capabilities=None,
            condition_type=proj_row[6] if len(proj_row) > 6 else 'none',
            condition_data=_parse_json_field(proj_row[7]) if len(proj_row) > 7 else None,
            project_type=proj_row[5] if len(proj_row) > 5 else 'mandatory',
            capability_tags=_parse_json_field(proj_row[8]) if len(proj_row) > 8 else None,
            next_step=_parse_json_field(proj_row[9]) if len(proj_row) > 9 else None,
            tasks=tasks_by_project.get(proj_row[0], []),
        )
        projects.append(project)
    return projects


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
    row = db.execute(
        text("SELECT id FROM scenarios WHERE id = :id"), {"id": scenario_id}
    ).fetchone()
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

    task_templates_result = db.execute(text("""
        SELECT id, phase_name, name, description, agent_type,
               required_capabilities, dependencies, order_in_phase,
               estimated_hours, priority, condition_type, condition_data, executor_type
        FROM scenario_tasks WHERE scenario_id = :scenario_id
    """), {"scenario_id": scenario.id})
    task_templates = []
    for row in task_templates_result:
        task_templates.append({
            "id": row[0], "phase_name": row[1], "name": row[2], "description": row[3],
            "agent_type": row[4], "required_capabilities": row[5], "dependencies": row[6],
            "order_in_phase": row[7], "estimated_hours": row[8], "priority": row[9],
            "condition_type": row[10] if len(row) > 10 else 'none',
            "condition_data": row[11] if len(row) > 11 else None,
            "executor_type": row[12] if len(row) > 12 else 'ai',
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
        task_templates=task_templates, projects=projects, fullset=fullset_data,
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
            db.execute(text("""
                INSERT INTO scenario_projects
                    (id, scenario_id, name, description, project_type, condition_type,
                     condition_data, next_step, capability_tags, order_index)
                VALUES (:id, :sid, :name, :desc, :ptype, :ctype, :cdata, :nstep, :ctags, :oindex)
            """), {
                "id": sp_id, "sid": db_scenario.id, "name": proj.get('name', ''),
                "desc": proj.get('description', ''), "ptype": proj_type,
                "ctype": proj.get('condition_type', 'none'),
                "cdata": json.dumps(proj.get('condition_data')) if proj.get('condition_data') else None,
                "nstep": json.dumps(proj.get('next_step')) if proj.get('next_step') else None,
                "ctags": json.dumps(proj.get('capability_tags', {})) if proj.get('capability_tags') else '{}',
                "oindex": idx,
            })
            for tidx, task in enumerate(proj.get('tasks', [])):
                task_id = task.get('id') or f"task-{uuid.uuid4().hex[:12]}"
                db.execute(text("""
                    INSERT INTO scenario_tasks
                        (id, scenario_id, project_id, phase_name, name, description, agent_type,
                         required_capabilities, dependencies, order_in_phase, estimated_hours,
                         priority, condition_type, condition_data, executor_type)
                    VALUES (:id, :sid, :pid, :phase, :name, :desc, :agent,
                            :rcaps, :deps, :oip, :ehours, :priority, :ctype, :cdata, :executor_type)
                """), {
                    "id": task_id, "sid": db_scenario.id, "pid": sp_id,
                    "phase": proj.get('name', ''), "name": task.get('name', ''),
                    "desc": task.get('description', ''), "agent": task.get('agent_type'),
                    "rcaps": json.dumps(task.get('required_capabilities', [])) if task.get('required_capabilities') else None,
                    "deps": json.dumps(task.get('dependencies', [])) if task.get('dependencies') else None,
                    "oip": task.get('order_in_phase', tidx), "ehours": task.get('estimated_hours'),
                    "priority": task.get('priority', 'medium'),
                    "ctype": task.get('condition_type', 'none'),
                    "cdata": json.dumps(task.get('condition_data')) if task.get('condition_data') else None,
                    "executor_type": task.get('executor_type', 'ai'),
                })
    elif steps_data:
        for idx, step in enumerate(steps_data):
            sp_id = step.get('id') or f"sp-{uuid.uuid4().hex[:12]}"
            db.execute(text("""
                INSERT INTO scenario_projects (id, scenario_id, name, description, order_index)
                VALUES (:id, :sid, :name, :desc, :oindex)
            """), {
                "id": sp_id, "sid": db_scenario.id, "name": step.get('name', ''),
                "desc": '', "oindex": step.get('order', idx),
            })

    db.commit()
    db.refresh(db_scenario)
    return db_scenario


def _update_scenario_with_projects(db: Session, scenario: Scenario, data: dict) -> Scenario:
    projects_data = data.get('projects')
    if projects_data is not None:
        db.execute(text("DELETE FROM scenario_tasks WHERE scenario_id = :sid"), {"sid": scenario.id})
        db.execute(text("DELETE FROM scenario_projects WHERE scenario_id = :sid"), {"sid": scenario.id})
        for idx, proj in enumerate(projects_data):
            sp_id = proj.get('id') or f"sp-{uuid.uuid4().hex[:12]}"
            proj_type = proj.get('project_type', proj.get('type', 'mandatory'))
            db.execute(text("""
                INSERT INTO scenario_projects
                    (id, scenario_id, name, description, project_type, condition_type,
                     condition_data, next_step, capability_tags, order_index)
                VALUES (:id, :sid, :name, :desc, :ptype, :ctype, :cdata, :nstep, :ctags, :oindex)
            """), {
                "id": sp_id, "sid": scenario.id, "name": proj.get('name', ''),
                "desc": proj.get('description', ''), "ptype": proj_type,
                "ctype": proj.get('condition_type', 'none'),
                "cdata": json.dumps(proj.get('condition_data')) if proj.get('condition_data') else None,
                "nstep": json.dumps(proj.get('next_step')) if proj.get('next_step') else None,
                "ctags": json.dumps(proj.get('capability_tags', {})) if proj.get('capability_tags') else '{}',
                "oindex": idx,
            })
            for tidx, task in enumerate(proj.get('tasks', [])):
                task_id = task.get('id') or f"task-{uuid.uuid4().hex[:12]}"
                db.execute(text("""
                    INSERT INTO scenario_tasks
                        (id, scenario_id, project_id, phase_name, name, description, agent_type,
                         required_capabilities, dependencies, order_in_phase, estimated_hours,
                         priority, condition_type, condition_data, executor_type)
                    VALUES (:id, :sid, :pid, :phase, :name, :desc, :agent,
                            :rcaps, :deps, :oip, :ehours, :priority, :ctype, :cdata, :executor_type)
                """), {
                    "id": task_id, "sid": scenario.id, "pid": sp_id,
                    "phase": proj.get('name', ''), "name": task.get('name', ''),
                    "desc": task.get('description', ''), "agent": task.get('agent_type'),
                    "rcaps": json.dumps(task.get('required_capabilities', [])) if task.get('required_capabilities') else None,
                    "deps": json.dumps(task.get('dependencies', [])) if task.get('dependencies') else None,
                    "oip": task.get('order_in_phase', tidx), "ehours": task.get('estimated_hours'),
                    "priority": task.get('priority', 'medium'),
                    "ctype": task.get('condition_type', 'none'),
                    "cdata": json.dumps(task.get('condition_data')) if task.get('condition_data') else None,
                    "executor_type": task.get('executor_type', 'ai'),
                })
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
        db.execute(text("DELETE FROM scenario_tasks WHERE scenario_id = :sid"), {"sid": scenario_id})
        db.execute(text("DELETE FROM scenario_projects WHERE scenario_id = :sid"), {"sid": scenario_id})
        db.delete(scenario)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除场景失败: {str(e)}")
