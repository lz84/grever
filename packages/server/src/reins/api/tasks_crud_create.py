"""Task CRUD — Create endpoint (create_task)."""
import json
import uuid
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.task import Task, TaskCreate, TaskResponse
from models.project import Project
from reins.common.database import get_db
from services.tag_prerequisites import (
    validate_prerequisites, check_deprecated_tags, resolve_all_prerequisites, CircularDependencyError,
)
from reins.api.tasks_helpers import _validate_task_constraints
from reins.api.tasks_crud_helpers import _parse_json_list, _sync_depends_on_all

logger = logging.getLogger(__name__)
router = APIRouter(tags=["tasks"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task_data: TaskCreate, db: Session = Depends(get_db)):
    """Create Task — 统一通过 depends_on 设置依赖，并从 Project 继承 capability_tags"""
    project_id = getattr(task_data, 'project_id', None)
    if project_id and not getattr(task_data, 'capability_tags', None):
        project = db.query(Project).filter(Project.id == project_id).first()
        if project and project.capability_tags:
            task_data.capability_tags = project._parse_capability_tags()

    if project_id and not getattr(task_data, 'goal_id', None):
        project = db.query(Project).filter(Project.id == project_id).first()
        if project and project.goal_id:
            task_data.goal_id = project.goal_id

    # Sprint 98 B98-5: capability_tags 前置标签校验
    strict_mode = getattr(task_data, 'strict_mode', True)
    if strict_mode is None:
        strict_mode = True
    capability_tags = getattr(task_data, 'capability_tags', None) or {}
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

    tag_warnings, auto_added_tags = [], []
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
                    detail={"error": "missing_prerequisites", "message": f"Missing prerequisites for capability tags: {missing}",
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
                    task_data.capability_tags = capability_tags
        for dw in check_deprecated_tags(cap_list):
            tag_warnings.append({"type": "deprecated_tag", "tag_id": dw["tag_id"],
                "message": f"Tag {dw['tag_id']} is deprecated. Consider replacing with {dw['replaced_by']}",
                "replaced_by": dw.get("replaced_by", "")})

    validation_error = _validate_task_constraints(task_data)
    if validation_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_failed", "message": validation_error})

    # 铁律四：需要验证的任务必须设置验收标准
    needs_verification = getattr(task_data, 'needs_verification', True)
    if needs_verification is None:
        needs_verification = True
    if needs_verification:
        acceptance_criteria = getattr(task_data, 'acceptance_criteria', None)
        has_criteria = bool(acceptance_criteria and acceptance_criteria.strip())
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
                    "message": "needs_verification=True 的任务必须设置有效的 acceptance_criteria。"})

    task_dict = task_data.model_dump(exclude_none=True)
    task_dict["id"] = f"task-{uuid.uuid4().hex[:12]}"
    if "assigned_agent" not in task_data.model_dump(exclude_unset=True):
        task_dict["assigned_agent"] = None
    if isinstance(task_dict.get("depends_on"), list):
        task_dict["depends_on"] = json.dumps(task_dict["depends_on"])
    if isinstance(task_dict.get("capability_tags"), dict):
        task_dict["capability_tags"] = json.dumps(task_dict["capability_tags"])
    task_dict.pop("dependency_ids", None)
    task_dict.pop("strict_mode", None)
    if not task_dict.get("project_id"):
        task_dict["project_id"] = "proj-nexus-internal"

    now_ts = int(time.time())
    task_dict.setdefault("created_at", now_ts)
    task_dict.setdefault("updated_at", now_ts)

    db_task = Task(**task_dict)
    db.add(db_task)
    db.flush()

    depends_on_list = _parse_json_list(task_dict.get("depends_on"))
    if depends_on_list:
        _sync_depends_on_all(db_task.id, depends_on_list, old_deps=[], db=db, is_create=True)
    db.commit()
    db.refresh(db_task)

    from vigil.common.audit import audit_task_create
    audit_task_create(task_id=task_dict["id"], operator="system",
        details={"title": task_data.title, "project_id": task_data.project_id})

    result = db_task.to_dict()
    if tag_warnings:
        result["tag_warnings"] = tag_warnings
    if auto_added_tags:
        result["auto_added_tags"] = auto_added_tags
        result["auto_added_reason"] = f"auto-added {len(auto_added_tags)} prerequisite tags"
    return result
