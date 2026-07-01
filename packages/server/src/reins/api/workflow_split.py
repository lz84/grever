"""
Sprint 29-2: Workflow 确认后自动拆分为 Project

功能:
- POST /api/v1/workflows/{workflow_id}/confirm-and-split
  确认 Workflow 并按 DAG 节点自动拆分为多个 Project

⚠️ 数据库访问统一通过 get_db_manager()，不直接引用 DB_PATH
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import uuid
import json
from datetime import datetime

from reins.common.database import get_db, get_db_manager
from models import Workflow, Project, Task

router = APIRouter(prefix="/api/v1/workflows", tags=["workflow-split"])

class ConfirmSplitRequest(BaseModel):
    pass

class ConfirmSplitResponse(BaseModel):
    workflow_id: str
    workflow_status: str
    projects_created: int
    project_ids: List[str]
    tasks_created: int

def _get_workflow_dag(db: Session, workflow_id: str) -> Optional[dict]:
    """获取 workflow 的 DAG 数据"""
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        return None
    dag = json.loads(wf.dag) if isinstance(wf.dag, str) else (wf.dag or {"nodes": [], "edges": []})
    return {
        "id": wf.id,
        "name": wf.name,
        "status": wf.status,
        "goal_id": wf.goal_id,
        "dag": dag,
    }

@router.post("/{workflow_id}/confirm-and-split", response_model=ConfirmSplitResponse)
def confirm_and_split_workflow(
    workflow_id: str,
    req: ConfirmSplitRequest = ConfirmSplitRequest(),
    db: Session = Depends(get_db)
):
    """
    确认 Workflow 并按 DAG 节点自动拆分为多个 Project

    Bug fix (2026-04-26): 依赖引用从 DAG 节点 ID 映射为实际 Task ID
    """
    # 1. 获取 workflow
    wf = _get_workflow_dag(db, workflow_id)
    if not wf:
        raise HTTPException(404, f"Workflow '{workflow_id}' not found")

    # 2. 检查状态
    if wf["status"] != "draft":
        raise HTTPException(400, f"Workflow 状态为 '{wf['status']}'，仅 draft 状态可操作")

    now = datetime.now()

    # 3. 更新 workflow 状态
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if wf:
        wf.status = 'confirmed'
        wf.updated_at = now

    # 4. 遍历 DAG 节点并创建 Projects + Tasks
    dag = wf.dag
    dag = json.loads(dag) if isinstance(dag, str) else (dag or {"nodes": [], "edges": []})
    nodes = dag.get("nodes", [])
    edges = dag.get("edges", [])

    # DAG node_id → 实际创建的 task_id 映射
    node_to_task: Dict[str, str] = {}

    project_ids = []
    tasks_created = 0

    sorted_nodes = sorted(nodes, key=lambda n: n.get("order", 0))

    # 第一遍：创建所有 Task，建立映射
    for i, node in enumerate(sorted_nodes):
        node_title = node.get("title", node.get("name", "未命名阶段"))
        node_desc = node.get("description", "")
        node_order = node.get("order", i)
        node_type = node.get("type", "execution")

        project_id = f"proj-{uuid.uuid4().hex[:12]}"
        project_ids.append(project_id)

        new_project = Project(
            id=project_id,
            name=node_title,
            description=node_desc,
            goal_id=wf.goal_id,
            workflow_id=workflow_id,
            phase_order=node_order,
            status='pending',
            priority='medium',
            created_at=now,
            updated_at=now,
        )
        db.add(new_project)

        # 为所有类型的节点创建 Task（包括 execution, step, decision, milestone 等）
        # 这样可以确保所有的 DAG 节点都有对应的 task，避免依赖映射失败和空 projects
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        node_to_task[node["id"]] = task_id
        tasks_created += 1

        new_task = Task(
            id=task_id,
            title=node_title,
            description=node_desc,
            project_id=project_id,
            goal_id=wf.goal_id,
            assigned_agent='',
            status='todo',
            priority='medium',
            dependencies='[]',
            created_at=int(now.timestamp()),
            updated_at=int(now.timestamp()),
        )
        db.add(new_task)

    db.commit()

    # 第二遍：建立 Task 之间的依赖关系
    for i, node in enumerate(sorted_nodes):
        if node["id"] not in node_to_task:
            continue

        task_id = node_to_task[node["id"]]

        # 找所有指向当前节点的边，获取源节点的 task_id
        dep_task_ids = []
        for edge in edges:
            src = edge.get("source", edge.get("from", ""))
            tgt = edge.get("target", edge.get("to", ""))
            if tgt == node["id"] and src in node_to_task:
                dep_task_ids.append(node_to_task[src])

        if dep_task_ids:
            deps_json = json.dumps(dep_task_ids, ensure_ascii=False)
            task_obj = db.query(Task).filter(Task.id == task_id).first()
            if task_obj:
                task_obj.dependencies = deps_json
                task_obj.updated_at = int(datetime.now().timestamp())
    
    db.commit()

    return ConfirmSplitResponse(
        workflow_id=workflow_id,
        workflow_status="confirmed",
        projects_created=len(project_ids),
        project_ids=project_ids,
        tasks_created=tasks_created,
    )
