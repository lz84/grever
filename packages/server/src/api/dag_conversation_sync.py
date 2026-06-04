"""DAG → projects 同步引擎

将对话修改后的 DAG 节点同步到 projects 表。
workflow_step 对应的是 project（1:1，phase_order = node index）
"""

import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

def _sync_projects_from_dag(db: Session, workflow_id: str, result_dag: dict):
    """
    将 DAG 节点同步到 projects 表。

    DAG node → project (1:1, phase_order = node index in list)
    workflow_step 对应的是 project（phase_order 匹配），不是 task

    调用时机：confirm action 执行成功后，db.commit() 之前
    """
    nodes = result_dag.get("nodes", [])
    if not nodes:
        return

    # Step 1: 获取 workflow 的 goal_id
    wf_row = db.execute(
        text("SELECT goal_id FROM workflows WHERE id = :id"),
        {"id": workflow_id}
    ).fetchone()
    if not wf_row or not wf_row.goal_id:
        return
    goal_id = wf_row.goal_id

    # Step 2: 查询已有 projects（关联到该 workflow，按 phase_order 索引）
    existing_projects = {}
    rows = db.execute(
        text("SELECT id, name, phase_order FROM projects WHERE workflow_id = :wf_id"),
        {"wf_id": workflow_id}
    ).fetchall()
    for row in rows:
        existing_projects[row.phase_order] = row

    # Step 3: 遍历 DAG nodes，同步到 projects
    current_project_ids = set()
    for idx, node in enumerate(nodes):
        node_title = node.get("title") or node.get("name", "")
        node_desc = node.get("description", "") or ""
        phase_order = idx

        if phase_order in existing_projects:
            # 更新已有 project（名称/描述变化时）
            proj = existing_projects[phase_order]
            db.execute(
                text("UPDATE projects SET name=:name, description=:desc, updated_at=:now "
                     "WHERE id=:id"),
                {"name": node_title, "desc": node_desc,
                 "now": datetime.utcnow().isoformat(), "id": proj.id}
            )
            current_project_ids.add(proj.id)
        else:
            # 创建新 project
            new_id = f"proj-{uuid.uuid4().hex[:12]}"
            db.execute(
                text("INSERT INTO projects (id, name, description, goal_id, workflow_id, "
                     "phase_order, status, priority, created_at, updated_at) "
                     "VALUES (:id, :name, :desc, :goal_id, :wf_id, :phase_order, "
                     "'active', 'medium', :now, :now)"),
                {"id": new_id, "name": node_title, "desc": node_desc,
                 "goal_id": goal_id, "wf_id": workflow_id,
                 "phase_order": phase_order, "now": datetime.utcnow().isoformat()}
            )
            current_project_ids.add(new_id)

    # Step 4: 删除被移除的 projects（phase_order 不在当前 nodes 中）
    if current_project_ids:
        placeholders = ",".join([f"'{pid}'" for pid in current_project_ids])
        db.execute(
            text(f"DELETE FROM projects WHERE workflow_id = :wf_id AND id NOT IN ({placeholders})"),
            {"wf_id": workflow_id}
        )