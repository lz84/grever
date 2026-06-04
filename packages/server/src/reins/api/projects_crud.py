"""
项目 CRUD 端点 (GET/POST/PUT/PATCH/DELETE)
从 projects.py 拆分

Sprint 79: next_step auto-sync on depends_on changes.
"""
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.project import Project, ProjectCreate, ProjectUpdate, ProjectResponse, ProjectCreateWithArrayDeps
from shared.database import get_db

router = APIRouter()

def _serialize_depends_on(value):
    """Serialize depends_on to JSON string for DB storage"""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value)

def _parse_json_list(value):
    """Parse a JSON string or list to Python list"""
    if not value:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(value, list):
        return value
    return []

def _sync_project_next_step_on_create(project_id: str, depends_on: list, db: Session):
    """When a project is created with depends_on, update each parent's next_step."""
    for dep_id in depends_on:
        parent = db.query(Project).filter(Project.id == dep_id).first()
        if parent:
            parent_next = _parse_json_list(parent.next_step)
            if project_id not in parent_next:
                parent_next.append(project_id)
                parent.next_step = json.dumps(parent_next)

def _sync_project_next_step_on_update(project: Project, new_depends_on: list, db: Session):
    """When a project's depends_on changes, update bidirectional next_step."""
    old_depends_on = _parse_json_list(project.depends_on)

    # Remove this project from old parents' next_step
    for dep_id in old_depends_on:
        parent = db.query(Project).filter(Project.id == dep_id).first()
        if parent:
            parent_next = _parse_json_list(parent.next_step)
            parent_next = [x for x in parent_next if x != project.id]
            parent.next_step = json.dumps(parent_next)

    # Add this project to new parents' next_step
    for dep_id in new_depends_on:
        parent = db.query(Project).filter(Project.id == dep_id).first()
        if parent:
            parent_next = _parse_json_list(parent.next_step)
            if project.id not in parent_next:
                parent_next.append(project.id)
                parent.next_step = json.dumps(parent_next)

def _cleanup_project_next_step_on_delete(project: Project, db: Session):
    """When a project is deleted, clean up bidirectional references."""
    # Remove from parents' next_step
    old_depends_on = _parse_json_list(project.depends_on)
    for dep_id in old_depends_on:
        parent = db.query(Project).filter(Project.id == dep_id).first()
        if parent:
            parent_next = _parse_json_list(parent.next_step)
            parent_next = [x for x in parent_next if x != project.id]
            parent.next_step = json.dumps(parent_next)

    # Remove this project's ID from children's depends_on
    my_next_step = _parse_json_list(project.next_step)
    for child_id in my_next_step:
        child = db.query(Project).filter(Project.id == child_id).first()
        if child:
            child_deps = _parse_json_list(child.depends_on)
            child_deps = [x for x in child_deps if x != project.id]
            child.depends_on = json.dumps(child_deps) if child_deps else '[]'

def _do_sync_next_step(project, new_depends_on_raw, db: Session):
    """Common logic: update depends_on + sync next_step."""
    if isinstance(new_depends_on_raw, str):
        try:
            new_depends_on = json.loads(new_depends_on_raw)
        except (json.JSONDecodeError, TypeError):
            new_depends_on = []
    elif isinstance(new_depends_on_raw, list):
        new_depends_on = new_depends_on_raw
    else:
        new_depends_on = []

    project.depends_on = _serialize_depends_on(new_depends_on)
    _sync_project_next_step_on_update(project, new_depends_on, db)

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    """获取单个项目详情"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project.to_dict()

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project_data: ProjectCreateWithArrayDeps, db: Session = Depends(get_db)):
    """创建新项目，支持 Sprint 22 新增字段"""
    project_dict = project_data.model_dump(exclude_unset=True)
    depends_on_raw = project_dict.get('depends_on')
    if 'depends_on' in project_dict:
        project_dict['depends_on'] = _serialize_depends_on(project_dict['depends_on'])
    project_dict["id"] = f"proj-{uuid.uuid4().hex[:12]}"
    db_project = Project(**project_dict)
    db.add(db_project)
    db.flush()  # Get the ID

    # Sprint 79: Sync next_step for parent projects
    if depends_on_raw:
        deps = _parse_json_list(depends_on_raw)
        _sync_project_next_step_on_create(db_project.id, deps, db)

    db.commit()
    db.refresh(db_project)
    return db_project.to_dict()

@router.post("/with-deps", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project_with_deps(body: dict, db: Session = Depends(get_db)):
    """创建新项目，支持 depends_on 为数组格式"""
    # Extract and serialize depends_on before creating model
    depends_on = body.pop('depends_on', None)
    project_data = ProjectCreate(**body)
    project_dict = project_data.model_dump(exclude_unset=True)
    project_dict['depends_on'] = _serialize_depends_on(depends_on)
    project_dict["id"] = f"proj-{uuid.uuid4().hex[:12]}"
    db_project = Project(**project_dict)
    db.add(db_project)
    db.flush()

    # Sprint 79: Sync next_step
    if depends_on:
        deps = _parse_json_list(depends_on)
        _sync_project_next_step_on_create(db_project.id, deps, db)

    db.commit()
    db.refresh(db_project)
    return db_project.to_dict()

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, project_data: ProjectUpdate, db: Session = Depends(get_db)):
    """更新项目信息，支持 Sprint 22 新增字段"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    old_goal_id = project.goal_id
    new_goal_id = getattr(project_data, 'goal_id', None)

    for key, value in project_data.model_dump(exclude_unset=True).items():
        if key == 'depends_on':
            # Sprint 79: sync next_step when depends_on changes
            _do_sync_next_step(project, value, db)
        elif key == 'capability_tags' and value is not None:
            if isinstance(value, (dict, list)):
                setattr(project, key, json.dumps(value))
            elif isinstance(value, str):
                try:
                    json.loads(value)
                    setattr(project, key, value)
                except (json.JSONDecodeError, TypeError):
                    setattr(project, key, json.dumps({"raw": value}))
        else:
            setattr(project, key, value)
    project.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)

    if old_goal_id != new_goal_id:
        from models.task import Task
        db.query(Task).filter(Task.project_id == project_id).update(
            {"goal_id": new_goal_id, "updated_at": datetime.now(timezone.utc)},
            synchronize_session=False
        )
        db.commit()

    return project.to_dict()

@router.patch("/{project_id}", response_model=ProjectResponse)
def patch_project(project_id: str, project_data: dict, db: Session = Depends(get_db)):
    """部分更新项目（支持 depends_on 等字段的部分更新）"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    for key, value in project_data.items():
        if key == 'depends_on':
            # Sprint 79: sync next_step when depends_on changes
            _do_sync_next_step(project, value, db)
        elif key == 'capability_tags' and value is not None:
            if isinstance(value, (dict, list)):
                setattr(project, key, json.dumps(value))
            elif isinstance(value, str):
                try:
                    json.loads(value)
                    setattr(project, key, value)
                except (json.JSONDecodeError, TypeError):
                    setattr(project, key, json.dumps({"raw": value}))
        elif hasattr(project, key):
            setattr(project, key, value)
    project.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)
    return project.to_dict()

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    """删除项目（级联删除相关任务）"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Sprint 79: Clean up bidirectional next_step references
    _cleanup_project_next_step_on_delete(project, db)

    from models.task import Task, TaskDependency
    db.query(TaskDependency).filter(TaskDependency.task_id.in_(
        db.query(Task.id).filter(Task.project_id == project_id)
    )).delete(synchronize_session=False)
    db.query(Task).filter(Task.project_id == project_id).delete()
    db.delete(project)
    db.commit()
    return
