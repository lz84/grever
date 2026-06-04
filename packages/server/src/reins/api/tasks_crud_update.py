"""Task CRUD — Update endpoints (update_task, patch_task)."""
import json
import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.task import Task, TaskUpdate, TaskResponse
from models.project import Project
from reins.common.database import get_db
from persistence.tables import execution_logs
from services.tag_prerequisites import (
    validate_prerequisites, check_deprecated_tags, resolve_all_prerequisites, CircularDependencyError,
)
from reins.api.tasks_helpers import _validate_task_constraints, _get_goal_id_from_project, _update_goal_progress
from reins.api.tasks_crud_helpers import (
    _parse_json_list, _sync_depends_on_all, _probe_agent_on_assign,
    _unblock_downstream_tasks, _check_and_update_project_done,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["tasks"])


def _validate_tag_update(task_data, strict_mode, update_fields):
    """Validate capability_tags on update, return (tag_warnings, auto_added_tags)."""
    tag_warnings, auto_added_tags = [], []
    if 'capability_tags' in update_fields:
        capability_tags = update_fields['capability_tags']
        cap_list = []
        if isinstance(capability_tags, dict):
            for dim_caps in capability_tags.values():
                if isinstance(dim_caps, list):
                    cap_list.extend(dim_caps)
        elif isinstance(capability_tags, list):
            cap_list = capability_tags
        elif isinstance(capability_tags, str) and capability_tags.strip():
            try:
                parsed = json.loads(capability_tags)
                if isinstance(parsed, dict):
                    for dim_caps in parsed.values():
                        if isinstance(dim_caps, list):
                            cap_list.extend(dim_caps)
                elif isinstance(parsed, list):
                    cap_list = parsed
            except (json.JSONDecodeError, TypeError):
                pass
        if cap_list:
            try:
                validate_prerequisites(cap_list)
            except CircularDependencyError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "circular_dependency", "message": str(e), "type": "circular_dependency"})
            missing = validate_prerequisites(cap_list)
            if missing:
                if strict_mode:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"error": "missing_prerequisites", "message": f"Missing prerequisites: {missing}",
                                "type": "missing_prerequisites", "missing": missing})
                else:
                    all_tags = resolve_all_prerequisites(cap_list)
                    auto_added_tags = [t for t in all_tags if t not in cap_list]
                    if auto_added_tags:
                        if isinstance(capability_tags, dict):
                            for dim in ["business", "professional", "technical", "management"]:
                                if dim not in capability_tags:
                                    capability_tags[dim] = []
                                capability_tags[dim].extend(auto_added_tags)
                                break
                        update_fields['capability_tags'] = capability_tags
            for dw in check_deprecated_tags(cap_list):
                tag_warnings.append({"type": "deprecated_tag", "tag_id": dw["tag_id"],
                    "message": f"Tag {dw['tag_id']} is deprecated.", "replaced_by": dw.get("replaced_by", "")})
    return tag_warnings, auto_added_tags


def _check_acceptance_criteria(needs_verification, acceptance_criteria):
    """Verify that tasks needing verification have acceptance criteria."""
    has_criteria = bool(acceptance_criteria and str(acceptance_criteria).strip())
    if has_criteria:
        try:
            ac = json.loads(acceptance_criteria)
            if not isinstance(ac, dict) or not ac.get('criteria'):
                has_criteria = False
        except (json.JSONDecodeError, TypeError):
            has_criteria = False
    if not has_criteria:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "acceptance_criteria_required",
                "message": "needs_verification=True 的任务必须设置有效的 acceptance_criteria"})


def _check_context_md_on_complete(old_status, new_status, needs_verification, context_md):
    """Verify context_md is filled when completing a task that needs verification."""
    _done_statuses = ('done', 'completed', 'review_needed')
    if old_status not in _done_statuses and new_status in _done_statuses:
        if needs_verification:
            if not context_md or not str(context_md).strip():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "context_md_required",
                        "message": "needs_verification=True 的任务完成时必须填写 context_md。"})


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: str, task_data: TaskUpdate, db: Session = Depends(get_db)):
    """Update Task — 统一通过 depends_on 设置依赖"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    project_id = getattr(task_data, 'project_id', None) or task.project_id
    if project_id and not getattr(task_data, 'capability_tags', None):
        project = db.query(Project).filter(Project.id == project_id).first()
        if project and project.capability_tags:
            task_data.capability_tags = project._parse_capability_tags()

    if project_id and not getattr(task_data, 'goal_id', None):
        project = db.query(Project).filter(Project.id == project_id).first()
        if project and project.goal_id:
            task_data.goal_id = project.goal_id

    strict_mode = getattr(task_data, 'strict_mode', True)
    if strict_mode is None:
        strict_mode = True
    update_fields = task_data.dict(exclude_unset=True)

    tag_warnings, auto_added_tags = _validate_tag_update(task_data, strict_mode, update_fields)

    validation_error = _validate_task_constraints(task_data)
    if validation_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_failed", "message": validation_error})

    update_fields = task_data.dict(exclude_unset=True)
    new_needs_verification = update_fields.get('needs_verification', task.needs_verification)
    new_acceptance_criteria = update_fields.get('acceptance_criteria', task.acceptance_criteria)
    if new_needs_verification:
        _check_acceptance_criteria(new_needs_verification, new_acceptance_criteria)

    old_status = task.status
    _new_status = old_status
    _new_context_md = task.context_md
    _new_needs_verification = task.needs_verification
    for key, value in task_data.dict(exclude_unset=True).items():
        if key == 'status': _new_status = value
        elif key == 'context_md': _new_context_md = value
        elif key == 'needs_verification': _new_needs_verification = value
    _check_context_md_on_complete(old_status, _new_status, _new_needs_verification, _new_context_md)

    for key, value in task_data.dict(exclude_unset=True).items():
        if key == 'depends_on':
            new_deps = value if isinstance(value, list) else _parse_json_list(value)
            old_deps = _parse_json_list(task.depends_on)
            task.depends_on = json.dumps(new_deps) if new_deps else None
            _sync_depends_on_all(task_id, new_deps, old_deps, db=db)
        elif key == 'capability_tags' and value is not None:
            if isinstance(value, (dict, list)):
                setattr(task, key, json.dumps(value))
            elif isinstance(value, str):
                try:
                    json.loads(value)
                    setattr(task, key, value)
                except (json.JSONDecodeError, TypeError):
                    setattr(task, key, json.dumps({"raw": value}))
        elif key == 'dependency_ids':
            old_deps = _parse_json_list(task.depends_on)
            new_deps = value if isinstance(value, list) else []
            task.depends_on = json.dumps(new_deps) if new_deps else None
            _sync_depends_on_all(task_id, new_deps, old_deps, db=db)
        else:
            setattr(task, key, value)

    new_status = task.status
    new_assigned_agent = getattr(task, 'assigned_agent', None)

    if old_status not in ('in_progress', 'in_review', 'done') and new_status == 'in_progress':
        try:
            db.execute(execution_logs.insert().values(
                id=str(uuid.uuid4()), task_id=str(task_id), agent_id=task.assigned_agent or '',
                action='task_start',
                input=json.dumps({"old_status": old_status, "new_status": "in_progress"}),
                output=json.dumps({"task_id": task_id, "task_title": task.title,
                    "goal_id": _get_goal_id_from_project(db, task.project_id)}),
                status='success', duration_ms=0, created_at=datetime.now(),
                error_message='', result_summary='任务已开始',
                metadata=json.dumps({"source": "update_task_endpoint"}),
                connectivity_verified=True,
            ))
        except Exception as e:
            logger.warning(f"[P1-01] execution_logs task_start warning: {e}")

    task.updated_at = datetime.now()
    db.commit()
    db.refresh(task)

    if new_assigned_agent:
        _probe_agent_on_assign(new_assigned_agent, db)

    if old_status != task.status and task.status in ('done', 'completed', 'review_needed'):
        task_goal_id = _get_goal_id_from_project(db, task.project_id)
        if task_goal_id:
            _update_goal_progress(db, task_goal_id)
            db.commit()
        _unblock_downstream_tasks(task_id, db)
        if task.project_id:
            _check_and_update_project_done(task_id, task.project_id, db)

    result = task.to_dict()
    if tag_warnings:
        result["tag_warnings"] = tag_warnings
    if auto_added_tags:
        result["auto_added_tags"] = auto_added_tags
        result["auto_added_reason"] = f"auto-added {len(auto_added_tags)} prerequisite tags"
    return result


@router.patch("/{task_id}", response_model=TaskResponse)
def patch_task(task_id: str, task_data: dict, db: Session = Depends(get_db)):
    """Partial update Task — 统一通过 depends_on 设置依赖"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    project_id = task_data.get('project_id', None) or task.project_id
    if project_id and 'capability_tags' not in task_data:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project and project.capability_tags:
            task_data['capability_tags'] = project._parse_capability_tags()

    _patch_new_status = task_data.get('status', task.status)
    _patch_new_context_md = task_data.get('context_md', task.context_md)
    _patch_new_needs_verification = task_data.get('needs_verification', task.needs_verification)
    _check_context_md_on_complete(task.status, _patch_new_status, _patch_new_needs_verification, _patch_new_context_md)

    for key, value in task_data.items():
        if key == 'depends_on':
            new_deps = value if isinstance(value, list) else _parse_json_list(value)
            old_deps = _parse_json_list(task.depends_on)
            task.depends_on = json.dumps(new_deps) if new_deps else None
            _sync_depends_on_all(task_id, new_deps, old_deps, db=db)
        elif key == 'capability_tags' and value is not None:
            if isinstance(value, (dict, list)):
                setattr(task, key, json.dumps(value))
            elif isinstance(value, str):
                try:
                    json.loads(value)
                    setattr(task, key, value)
                except (json.JSONDecodeError, TypeError):
                    setattr(task, key, json.dumps({"raw": value}))
        elif key == 'dependency_ids':
            old_deps = _parse_json_list(task.depends_on)
            new_deps = value if isinstance(value, list) else []
            task.depends_on = json.dumps(new_deps) if new_deps else None
            _sync_depends_on_all(task_id, new_deps, old_deps, db=db)
        else:
            setattr(task, key, value)

    new_assigned_agent = getattr(task, 'assigned_agent', None)
    task.updated_at = datetime.now()
    db.commit()
    db.refresh(task)

    if new_assigned_agent:
        _probe_agent_on_assign(new_assigned_agent, db)

    if task.status in ('done', 'completed', 'review_needed'):
        task_goal_id = _get_goal_id_from_project(db, task.project_id)
        if task_goal_id:
            _update_goal_progress(db, task_goal_id)
            db.commit()
        _unblock_downstream_tasks(task_id, db)
        if task.project_id:
            _check_and_update_project_done(task_id, task.project_id, db)

    return task.to_dict()
