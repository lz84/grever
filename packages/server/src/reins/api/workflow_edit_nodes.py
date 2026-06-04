"""WorkflowEditLogic — Node CRUD operations — split from workflow_edit_logic.py"""

import uuid
from typing import Dict

from reins.api.workflow_edit_db import WorkflowEditDbMixin

class WorkflowEditNodeMixin(WorkflowEditDbMixin):
    """Node CRUD operations for workflow DAG editing."""

    def _add_node(self, dag: dict, req: dict) -> dict:
        node = req.get("node", {})
        node_id = f"step-{uuid.uuid4().hex[:8]}"
        new_node = {
            "id": node_id,
            "title": node.get("title", node.get("name", "")),
            "description": node.get("description", ""),
            "type": node.get("type", "execution"),
            "status": "pending",
            "dependencies": node.get("dependencies", []),
        }
        if node.get("assignee"):
            new_node["assignee"] = node["assignee"]
        dag["nodes"].append(new_node)
        return dag

    def _update_node(self, dag: dict, req: dict) -> dict:
        node_id = req.get("node_id")
        updates = req.get("updates", {})
        node = next((n for n in dag.get("nodes", []) if n["id"] == node_id), None)
        if node:
            if "title" in updates:
                node["title"] = updates["title"]
            if "description" in updates:
                node["description"] = updates["description"]
            if "type" in updates:
                node["type"] = updates["type"]
            if "assignee" in updates:
                node["assignee"] = updates["assignee"]
        return dag

    def _delete_node(self, dag: dict, req: dict) -> dict:
        node_id = req.get("node_id")
        dag["nodes"] = [n for n in dag.get("nodes", []) if n["id"] != node_id]
        dag["edges"] = [
            e for e in dag.get("edges", [])
            if self._edge_src(e) != node_id and self._edge_tgt(e) != node_id
        ]
        return dag

    def edit_workflow_dag(self, workflow_id: str, req):
        """Workflow DAG 统一编辑接口"""
        from fastapi import HTTPException
        from reins.api.workflow_edit import DagEditResponse

        if hasattr(req, 'model_dump'):
            req = req.model_dump()

        wf = self._get_workflow_dag(workflow_id)
        if not wf:
            raise HTTPException(404, "Workflow not found")
        self._check_editable(wf["status"])

        dag = wf["dag"]
        action = req.get("action")

        if action == "add_node":
            dag = self._add_node(dag, req)
        elif action == "update_node":
            dag = self._update_node(dag, req)
        elif action == "delete_node":
            dag = self._delete_node(dag, req)
        elif action == "add_edge":
            dag = self._add_edge(dag, req)
        elif action == "delete_edge":
            dag = self._delete_edge(dag, req)
        else:
            raise HTTPException(400, f"不支持的编辑动作: {action}")

        is_valid, err = self._validate_dag(dag)
        if not is_valid:
            raise HTTPException(400, err)

        self._save_dag(workflow_id, dag)
        steps_count = self._sync_steps(workflow_id, dag)

        return DagEditResponse(
            workflow_id=workflow_id, name=wf["name"], status=wf["status"],
            dag=dag, steps_synced=steps_count,
        )

    def add_workflow_node(self, workflow_id: str, req):
        """添加 Workflow 节点"""
        from fastapi import HTTPException
        from reins.api.workflow_edit import DagEditResponse

        if hasattr(req, 'model_dump'):
            req = req.model_dump()

        wf = self._get_workflow_dag(workflow_id)
        if not wf:
            raise HTTPException(404, "Workflow not found")
        self._check_editable(wf["status"])

        dag = wf["dag"]
        existing_ids = {n["id"] for n in dag.get("nodes", [])}

        node_id = f"step-{uuid.uuid4().hex[:8]}"
        new_node = {
            "id": node_id,
            "title": req.get("title"),
            "description": req.get("description", ""),
            "type": req.get("node_type", "execution"),
            "status": "pending",
            "dependencies": req.get("dependencies", []),
        }
        if req.get("assignee"):
            new_node["assignee"] = req["assignee"]

        dag["nodes"].append(new_node)

        for dep_id in req.get("dependencies", []):
            if dep_id in existing_ids:
                exists = any(
                    self._edge_src(e) == dep_id and self._edge_tgt(e) == node_id
                    for e in dag.get("edges", [])
                )
                if not exists:
                    dag.setdefault("edges", []).append({
                        "source": dep_id, "target": node_id,
                    })

        is_valid, err = self._validate_dag(dag)
        if not is_valid:
            raise HTTPException(400, err)

        self._save_dag(workflow_id, dag)
        steps_count = self._sync_steps(workflow_id, dag)

        return DagEditResponse(
            workflow_id=workflow_id, name=wf["name"], status=wf["status"],
            dag=dag, steps_synced=steps_count,
        )

    def update_workflow_node(self, workflow_id: str, node_id: str, req):
        """更新 Workflow 节点属性"""
        from fastapi import HTTPException
        from reins.api.workflow_edit import DagEditResponse

        if hasattr(req, 'model_dump'):
            req = req.model_dump(exclude_unset=True)

        wf = self._get_workflow_dag(workflow_id)
        if not wf:
            raise HTTPException(404, "Workflow not found")
        self._check_editable(wf["status"])

        dag = wf["dag"]
        node = next((n for n in dag.get("nodes", []) if n["id"] == node_id), None)
        if not node:
            raise HTTPException(404, f"Node '{node_id}' not found")

        if req.get("title") is not None:
            node["title"] = req["title"]
        if req.get("description") is not None:
            node["description"] = req["description"]
        if req.get("node_type") is not None:
            node["type"] = req["node_type"]
        if req.get("assignee") is not None:
            node["assignee"] = req["assignee"]

        self._save_dag(workflow_id, dag)
        steps_count = self._sync_steps(workflow_id, dag)

        return DagEditResponse(
            workflow_id=workflow_id, name=wf["name"], status=wf["status"],
            dag=dag, steps_synced=steps_count,
        )

    def delete_workflow_node(self, workflow_id: str, node_id: str):
        """删除 Workflow 节点"""
        from fastapi import HTTPException
        from reins.api.workflow_edit import DagEditResponse

        wf = self._get_workflow_dag(workflow_id)
        if not wf:
            raise HTTPException(404, "Workflow not found")
        self._check_editable(wf["status"])

        dag = wf["dag"]
        target = next((n for n in dag.get("nodes", []) if n["id"] == node_id), None)
        if not target:
            raise HTTPException(404, f"Node '{node_id}' not found")

        dag["nodes"] = [n for n in dag.get("nodes", []) if n["id"] != node_id]
        dag["edges"] = [
            e for e in dag.get("edges", [])
            if self._edge_src(e) != node_id and self._edge_tgt(e) != node_id
        ]

        self._save_dag(workflow_id, dag)
        steps_count = self._sync_steps(workflow_id, dag)

        return DagEditResponse(
            workflow_id=workflow_id, name=wf["name"], status=wf["status"],
            dag=dag, steps_synced=steps_count,
        )

    def reorder_workflow_nodes(self, workflow_id: str, req):
        """重排 Workflow 节点顺序"""
        from fastapi import HTTPException
        from reins.api.workflow_edit import DagEditResponse

        if hasattr(req, 'model_dump'):
            req = req.model_dump()

        wf = self._get_workflow_dag(workflow_id)
        if not wf:
            raise HTTPException(404, "Workflow not found")
        self._check_editable(wf["status"])

        dag = wf["dag"]
        node_map = {n["id"]: n for n in dag.get("nodes", [])}
        node_ids = req.get("node_ids", [])

        for nid in node_ids:
            if nid not in node_map:
                raise HTTPException(404, f"Node '{nid}' not found")

        ordered = []
        for nid in node_ids:
            node = node_map[nid].copy()
            node["order"] = len(ordered)
            ordered.append(node)
        dag["nodes"] = ordered

        self._save_dag(workflow_id, dag)
        steps_count = self._sync_steps(workflow_id, dag)

        return DagEditResponse(
            workflow_id=workflow_id, name=wf["name"], status=wf["status"],
            dag=dag, steps_synced=steps_count,
        )
