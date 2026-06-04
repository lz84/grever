"""WorkflowEditLogic — Edge CRUD operations — split from workflow_edit_logic.py"""

from typing import Dict

from reins.api.workflow_edit_db import WorkflowEditDbMixin

class WorkflowEditEdgeMixin(WorkflowEditDbMixin):
    """Edge CRUD operations for workflow DAG editing."""

    def _add_edge(self, dag: dict, req: dict) -> dict:
        source = req.get("source")
        target = req.get("target")
        label = req.get("label")
        edge = {"source": source, "target": target}
        if label:
            edge["label"] = label
        dag.setdefault("edges", []).append(edge)
        return dag

    def _delete_edge(self, dag: dict, req: dict) -> dict:
        source = req.get("source")
        target = req.get("target")
        dag["edges"] = [
            e for e in dag.get("edges", [])
            if not (self._edge_src(e) == source and self._edge_tgt(e) == target)
        ]
        return dag

    def add_workflow_edge(self, workflow_id: str, req):
        """添加 Workflow 边"""
        from fastapi import HTTPException
        from reins.api.workflow_edit import DagEditResponse

        if hasattr(req, 'model_dump'):
            req = req.model_dump()

        wf = self._get_workflow_dag(workflow_id)
        if not wf:
            raise HTTPException(404, "Workflow not found")
        self._check_editable(wf["status"])

        dag = wf["dag"]
        node_ids = {n["id"] for n in dag.get("nodes", [])}
        source = req.get("source")
        target = req.get("target")

        if source not in node_ids:
            raise HTTPException(404, f"源节点 '{source}' 不存在")
        if target not in node_ids:
            raise HTTPException(404, f"目标节点 '{target}' 不存在")

        exists = any(
            self._edge_src(e) == source and self._edge_tgt(e) == target
            for e in dag.get("edges", [])
        )
        if exists:
            raise HTTPException(400, f"边 {source}→{target} 已存在")

        edge = {"source": source, "target": target}
        if req.get("label"):
            edge["label"] = req["label"]
        dag.setdefault("edges", []).append(edge)

        is_valid, err = self._validate_dag(dag)
        if not is_valid:
            dag["edges"].pop()
            raise HTTPException(400, err)

        self._save_dag(workflow_id, dag)
        steps_count = self._sync_steps(workflow_id, dag)

        return DagEditResponse(
            workflow_id=workflow_id, name=wf["name"], status=wf["status"],
            dag=dag, steps_synced=steps_count,
        )

    def delete_workflow_edge(self, workflow_id: str, source: str, target: str):
        """删除 Workflow 边"""
        from fastapi import HTTPException
        from reins.api.workflow_edit import DagEditResponse

        wf = self._get_workflow_dag(workflow_id)
        if not wf:
            raise HTTPException(404, "Workflow not found")
        self._check_editable(wf["status"])

        dag = wf["dag"]
        orig_count = len(dag.get("edges", []))
        dag["edges"] = [
            e for e in dag.get("edges", [])
            if not (self._edge_src(e) == source and self._edge_tgt(e) == target)
        ]

        if len(dag["edges"]) == orig_count:
            raise HTTPException(404, f"边 {source}→{target} 不存在")

        self._save_dag(workflow_id, dag)
        steps_count = self._sync_steps(workflow_id, dag)

        return DagEditResponse(
            workflow_id=workflow_id, name=wf["name"], status=wf["status"],
            dag=dag, steps_synced=steps_count,
        )
