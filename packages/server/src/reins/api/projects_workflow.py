"""项目工作流端点"""
import json
from fastapi import APIRouter, HTTPException, Query
from reins.common.database import get_db_manager
from sqlalchemy import text

router = APIRouter()

@router.get("/{project_id}/diagram")
def get_project_diagram(project_id: str):
    """获取项目 DAG 图"""
    engine = get_db_manager().engine
    with engine.connect() as conn:
        proj = conn.execute(text(
            "SELECT id, name, description, status FROM projects WHERE id = :id"
        ), {"id": project_id}).fetchone()
        
        if not proj:
            raise HTTPException(404, "Project not found")
        
        all_tasks = conn.execute(text("""
            SELECT id, title, description, project_id, goal_id, 
                   assigned_agent, status, priority, dependencies, 
                   depends_on, parent_id, created_at
            FROM tasks 
            WHERE project_id = :pid
            ORDER BY priority, created_at
        """), {"pid": project_id}).fetchall()
        
        task_map = {t.id: t for t in all_tasks}
        nodes = []
        edges = []
        
        for task in all_tasks:
            nodes.append({
                "id": task.id,
                "step_id": task.id,
                "title": task.title,
                "description": task.description or "",
                "type": "execution",
                "status": task.status,
                "assignee": task.assigned_agent or "",
            })
            
            if task.dependencies:
                try:
                    deps = json.loads(task.dependencies) if isinstance(task.dependencies, str) else task.dependencies
                    if deps:
                        for dep_id in deps:
                            if dep_id in task_map:
                                edges.append({"id": f"{dep_id}-{task.id}", "source": dep_id, "target": task.id, "label": ""})
                except (json.JSONDecodeError, TypeError):
                    pass
            
            if task.depends_on:
                try:
                    deps = json.loads(task.depends_on) if isinstance(task.depends_on, str) else task.depends_on
                    if deps:
                        for dep_id in deps:
                            if dep_id in task_map:
                                edge_id = f"{task.id}-{dep_id}"
                                if not any(e["id"] == edge_id for e in edges):
                                    edges.append({"id": edge_id, "source": task.id, "target": dep_id, "label": ""})
                except (json.JSONDecodeError, TypeError):
                    pass
        
        dag = {"nodes": [n["id"] for n in nodes], "edges": [[e["source"], e["target"]] for e in edges]}
        
        return {
            "project_id": proj.id,
            "name": proj.name,
            "status": proj.status,
            "nodes": nodes,
            "edges": edges,
            "dag": dag,
        }

@router.get("/{project_id}/task-tree")
def get_project_task_tree(project_id: str):
    """获取项目任务树"""
    engine = get_db_manager().engine
    with engine.connect() as conn:
        proj = conn.execute(text(
            "SELECT id, name, description, status FROM projects WHERE id = :id"
        ), {"id": project_id}).fetchone()
        
        if not proj:
            raise HTTPException(404, "Project not found")
        
        all_tasks = conn.execute(text("""
            SELECT id, title, description, project_id, goal_id, 
                   assigned_agent, status, priority, dependencies, 
                   depends_on, parent_id, created_at, due_date
            FROM tasks 
            WHERE project_id = :pid
            ORDER BY priority, created_at
        """), {"pid": project_id}).fetchall()
        
        task_list = []
        for t in all_tasks:
            task_list.append({
                "id": t.id,
                "title": t.title,
                "description": t.description or "",
                "project_id": t.project_id,
                "goal_id": t.goal_id,
                "assigned_agent": t.assigned_agent or "",
                "status": t.status,
                "priority": t.priority,
                "parent_id": t.parent_id,
                "created_at": t.created_at,
                "due_date": t.due_date,
                "children": [],
            })
        
        task_map = {t["id"]: t for t in task_list}
        root_tasks = []
        
        for task in task_list:
            parent_id = task["parent_id"]
            if parent_id and parent_id in task_map:
                task_map[parent_id]["children"].append(task)
            else:
                root_tasks.append(task)
        
        return {
            "project_id": proj.id,
            "project_name": proj.name,
            "project_status": proj.status,
            "root_tasks": root_tasks,
        }

@router.patch("/{project_id}/status")
def update_project_status(project_id: str, status: str = Query(..., description="目标状态")):
    """更新项目状态"""
    from models.project import ProjectStatus
    valid_statuses = [v for k, v in vars(ProjectStatus).items()
                     if isinstance(v, str) and not k.startswith('_') and not callable(v)]
    
    if status not in valid_statuses:
        raise HTTPException(400, f"无效状态 '{status}'，可选: {', '.join(valid_statuses)}")
    
    engine = get_db_manager().engine
    
    with engine.connect() as conn:
        proj = conn.execute(text(
            "SELECT id, name, status FROM projects WHERE id = :id"
        ), {"id": project_id}).fetchone()
        
        if not proj:
            raise HTTPException(404, "Project not found")
        
        current_status = proj.status
        
        if current_status == status:
            return {
                "project_id": project_id,
                "current_status": current_status,
                "new_status": status,
                "message": "Already in target status",
                "tasks_affected": 0,
            }
        
        tasks_affected = 0
        
        if status == "on_hold" and current_status in ("active", "in_progress"):
            r1 = conn.execute(text(
                "UPDATE tasks SET status='todo' WHERE project_id=:pid AND status='in_progress'"
            ), {"pid": project_id})
            tasks_affected = r1.rowcount
        
        conn.execute(text(
            "UPDATE projects SET status=:st WHERE id=:pid"
        ), {"pid": project_id, "st": status})
        
        conn.commit()
        
        return {
            "project_id": project_id,
            "previous_status": current_status,
            "new_status": status,
            "tasks_affected": tasks_affected,
        }
