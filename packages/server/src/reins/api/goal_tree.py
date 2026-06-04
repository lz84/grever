from fastapi import APIRouter, HTTPException
from reins.common.database import get_db_manager
from sqlalchemy import text

router = APIRouter(prefix="/api/v1/goals", tags=["goal-tree"])

@router.get("/{goal_id}/tree")
def get_goal_tree(goal_id: str):
    """获取 Goal → Project → Task 的树状结构
    
    数据源与 GoalDetail 页面保持一致：
    - projects: 通过 goal_id 关联（含 workflow 拆解产生的 projects）
    - tasks: 通过 project_id 关联
    """
    engine = get_db_manager().engine
    
    # 获取 Goal
    with engine.connect() as conn:
        goal = conn.execute(text(
            "SELECT id, title, description, status, priority, created_at FROM goals WHERE id = :id"
        ), {"id": goal_id}).fetchone()
    
    if not goal:
        from fastapi import HTTPException
        raise HTTPException(404, "Goal not found")
    
    # 获取 Projects（与 GoalDetail 页 projectsApi.list({ goal_id }) 完全一致）
    with engine.connect() as conn:
        projects = conn.execute(text(
            "SELECT id, name, description, status, priority, phase_order, goal_id FROM projects WHERE goal_id = :gid ORDER BY phase_order"
        ), {"gid": goal_id}).fetchall()
    
    # 获取 Tasks — 通过 project_id 关联（而非 goal_id）
    # 很多 task 的 goal_id 为 NULL 或其他值，但 project_id 是正确的
    # 所以通过 project_id IN (projects of this goal) 来获取
    project_ids = [p.id for p in projects]
    if project_ids:
        placeholders = ",".join([f":p{i}" for i in range(len(project_ids))])
        params = {f"p{i}": pid for i, pid in enumerate(project_ids)}
        with engine.connect() as conn:
            tasks = conn.execute(text(
                f"SELECT id, title, description, status, priority, project_id, goal_id, assigned_agent FROM tasks WHERE project_id IN ({placeholders}) ORDER BY project_id, created_at"
            ), params).fetchall()
    else:
        tasks = []
    
    # 按 project_id 分组 tasks
    task_map_by_project = {}
    for t in tasks:
        if t.project_id:
            if t.project_id not in task_map_by_project:
                task_map_by_project[t.project_id] = []
            task_map_by_project[t.project_id].append({
                "id": t.id,
                "title": t.title or "未命名任务",
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "assigned_agent": t.assigned_agent,
                "type": "task"
            })
    
    # 构建树
    # Orphan tasks (no project_id) are NOT shown at goal level.
    # Goal children = only projects. Tasks live under their projects.
    tree = {
        "id": goal.id,
        "title": goal.title,
        "description": goal.description,
        "status": goal.status,
        "priority": goal.priority,
        "type": "goal",
        "children": []
    }
    
    for p in projects:
        node = {
            "id": p.id,
            "title": p.name or "未命名阶段",
            "description": p.description,
            "status": p.status,
            "priority": p.priority,
            "phase_order": p.phase_order,
            "type": "project",
            "children": task_map_by_project.get(p.id, [])
        }
        tree["children"].append(node)
    
    return tree