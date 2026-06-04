from fastapi import APIRouter, HTTPException
from reins.common.database import get_db_manager
from sqlalchemy import text

router = APIRouter(prefix="/api/v1/workflows", tags=["workflow-diagram"])

@router.get("/{workflow_id}/diagram")
def get_workflow_diagram(workflow_id: str):
    """获取 Workflow DAG 图数据（用于 React Flow 可视化）"""
    engine = get_db_manager().engine
    with engine.connect() as conn:
        # 获取 Workflow 信息
        wf = conn.execute(text(
            "SELECT id, name, description, status, dag FROM workflows WHERE id = :id"
        ), {"id": workflow_id}).fetchone()
        
        if not wf:
            raise HTTPException(404, "Workflow not found")
        
        import json
        dag = json.loads(wf.dag) if isinstance(wf.dag, str) else (wf.dag if wf.dag else {})
        nodes = dag.get("nodes", [])
        edges = dag.get("edges", [])
        
        # 节点列表
        node_list = []
        for n in nodes:
            node_type = n.get("type", "execution")
            node_list.append({
                "id": n.get("id", str(n.get("step_id", ""))),
                "step_id": n.get("step_id", ""),
                "title": n.get("title", n.get("name", "未命名")),
                "description": n.get("description", ""),
                "type": node_type,  # execution/notification/decision/parallel/milestone
                "status": n.get("status", "pending"),
                "assignee": n.get("assignee", n.get("assigned_to", "")),
            })
        
        # 边列表 — support both {source,target} and {from,to} formats
        edge_list = []
        for e in edges:
            src = e.get("source") or e.get("from", "")
            tgt = e.get("target") or e.get("to", "")
            edge_list.append({
                "id": e.get("id", f"{src}-{tgt}"),
                "source": str(src),
                "target": str(tgt),
                "label": e.get("condition", e.get("label", "")),
            })
        
        return {
            "workflow_id": wf.id,
            "name": wf.name,
            "status": wf.status,
            "nodes": node_list,
            "edges": edge_list
        }
