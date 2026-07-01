"""DAG → projects 同步引擎

将对话修改后的 DAG 节点同步到 projects 表。
workflow_step 对应的是 project（1:1，phase_order = node index）
"""

import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from models.workflow import Workflow
from models.project import Project

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
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf or not wf.goal_id:
        return
    goal_id = wf.goal_id

    # Step 2: 查询已有 projects（关联到该 workflow，按 phase_order 索引）
    existing_projects = {}
    rows = db.query(Project).filter(Project.workflow_id == workflow_id).all()
    for proj in rows:
        existing_projects[proj.phase_order] = proj

    # Step 3: 遍历 DAG nodes，同步到 projects
    current_project_ids = set()
    now_ts = int(datetime.utcnow().timestamp())
    for idx, node in enumerate(nodes):
        node_title = node.get("title") or node.get("name", "")
        node_desc = node.get("description", "") or ""
        phase_order = idx

        if phase_order in existing_projects:
            # 更新已有 project（名称/描述变化时）
            proj = existing_projects[phase_order]
            proj.name = node_title
            proj.description = node_desc
            proj.updated_at = now_ts
            current_project_ids.add(proj.id)
        else:
            # 创建新 project
            new_id = f"proj-{uuid.uuid4().hex[:12]}"
            new_proj = Project(
                id=new_id,
                name=node_title,
                description=node_desc,
                goal_id=goal_id,
                workflow_id=workflow_id,
                phase_order=phase_order,
                status="active",
                priority="medium",
                created_at=now_ts,
                updated_at=now_ts,
            )
            db.add(new_proj)
            current_project_ids.add(new_id)

    # Step 4: 删除被移除的 projects（phase_order 不在当前 nodes 中）
    if current_project_ids:
        db.query(Project).filter(
            Project.workflow_id == workflow_id,
            Project.id.notin_(current_project_ids)
        ).delete(synchronize_session=False)