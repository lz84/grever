"""GRASP knowledge + graph endpoints — split from grasp_router.py"""

from typing import List, Optional

from fastapi import APIRouter, Query

from grasp.api.grasp_helpers import _load_cognitions, _try_load_graph_data

router = APIRouter()

@router.get("/knowledge")
def list_knowledge(
    type: Optional[str] = Query(default=None, description="Filter by cognition type"),
    tag: Optional[List[str]] = Query(default=None, description="Filter by tag(s)"),
):
    """列出所有认知，支持按类型和标签过滤。"""
    try:
        cognitions = _load_cognitions()
        if type:
            cognitions = [c for c in cognitions if c.get("type") == type]
        if tag:
            tag_set = set(t.lower() for t in tag)
            cognitions = [c for c in cognitions if any(
                t.lower() in tag_set for t in c.get("tags", [])
            )]
        return {
            "status": "success",
            "total": len(cognitions),
            "cognitions": cognitions,
            "items": cognitions,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "total": 0, "cognitions": [], "items": []}

@router.get("/graph")
def get_graph(q: Optional[str] = Query(default=None, description="Search keyword")):
    """返回知识图谱数据（nodes/edges）。"""
    try:
        nodes, edges = _try_load_graph_data()
        if q:
            q_lower = q.lower()
            nodes = [n for n in nodes if q_lower in n["label"].lower() or q_lower in n.get("category", "").lower()]
            visible_ids = {n["id"] for n in nodes}
            edges = [e for e in edges if e["from"] in visible_ids and e["to"] in visible_ids]
        return {
            "status": "success",
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "nodes": [], "edges": []}
