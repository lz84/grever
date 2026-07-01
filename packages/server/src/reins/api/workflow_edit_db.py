"""WorkflowEditLogic — DB helpers + DAG validation — split from workflow_edit_logic.py"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from sqlalchemy import text
from sqlalchemy.orm import Session

from reins.common.database import get_db_manager
from models import Workflow

class WorkflowEditDbMixin:
    """DB access + DAG validation helpers for workflow editing."""

    @property
    def _engine(self):
        return get_db_manager().engine

    def _get_session(self) -> Session:
        return get_db_manager().get_session()

    def _get_workflow_dag(self, workflow_id: str) -> Optional[dict]:
        """获取 workflow 的 DAG 数据"""
        workflow = self._get_session().query(Workflow).filter(Workflow.id == workflow_id).first()

        if not workflow:
            return None

        dag = json.loads(workflow.dag) if isinstance(workflow.dag, str) else (workflow.dag or {"nodes": [], "edges": []})
        return {
            "id": workflow.id,
            "name": workflow.name,
            "status": workflow.status,
            "dag": dag,
        }

    def _save_dag(self, workflow_id: str, dag: dict):
        """保存 DAG 到数据库"""
        now = datetime.now().isoformat()
        session = self._get_session()
        session.query(Workflow).filter(Workflow.id == workflow_id).update({
            "dag": json.dumps(dag, ensure_ascii=False),
            "updated_at": now,
        })
        session.commit()

    @staticmethod
    def _edge_src(edge: dict) -> str:
        return str(edge.get("source", edge.get("from", "")))

    @staticmethod
    def _edge_tgt(edge: dict) -> str:
        return str(edge.get("target", edge.get("to", "")))

    def _validate_dag(self, dag: dict) -> tuple:
        """验证 DAG 有效性"""
        nodes = dag.get("nodes", [])
        edges = dag.get("edges", [])
        node_ids = {n["id"] for n in nodes}

        for edge in edges:
            src = self._edge_src(edge)
            tgt = self._edge_tgt(edge)
            if src not in node_ids:
                return False, f"边引用了不存在的源节点: {src}"
            if tgt not in node_ids:
                return False, f"边引用了不存在的目标节点: {tgt}"

        adj: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
        in_degree: Dict[str, int] = {n["id"]: 0 for n in nodes}

        for edge in edges:
            src = self._edge_src(edge)
            tgt = self._edge_tgt(edge)
            if src in adj and tgt in adj:
                adj[src].append(tgt)
                in_degree[tgt] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            node = queue.pop(0)
            visited += 1
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited != len(nodes):
            return False, "DAG 存在循环依赖，无法保存"
        return True, ""

    def _sync_steps(self, workflow_id: str, dag: dict) -> int:
        """将 DAG 同步到 workflow_steps 表（UPSERT 策略）"""
        nodes = dag.get("nodes", [])
        now = datetime.now().isoformat()

        with self._engine.begin() as conn:
            for i, node in enumerate(nodes):
                nid = node["id"]
                node_type = node.get("type", "execution")
                deps = json.dumps(node.get("dependencies", []), ensure_ascii=False)
                assignee = node.get("assignee", "")
                title = node.get("title", node.get("name", ""))
                desc = node.get("description", "")
                input_data = json.dumps({"node_type": node_type}, ensure_ascii=False)

                # EXCEPTION: SQLite ON CONFLICT upsert, not easily expressible in ORM
                conn.execute(text("""
                    INSERT INTO workflow_steps
                    (id, workflow_id, name, description, status, dependencies,
                     "order", agent_id, input_data, output_data, retry_count, max_retries,
                     created_at, updated_at)
                    VALUES (:id, :wf, :name, :desc, 'pending', :deps,
                            :ord, :agent, :input, '{}', 0, 3, :now, :now)
                    ON CONFLICT(id) DO UPDATE SET
                        workflow_id = :wf,
                        name = :name,
                        description = :desc,
                        status = 'pending',
                        dependencies = :deps,
                        "order" = :ord,
                        agent_id = :agent,
                        input_data = :input,
                        updated_at = :now
                """), {
                    "id": nid,
                    "wf": workflow_id,
                    "name": title,
                    "desc": desc,
                    "deps": deps,
                    "ord": i,
                    "agent": assignee,
                    "input": input_data,
                    "now": now,
                })

        return len(nodes)

    @staticmethod
    def _check_editable(status_val: str):
        """检查 workflow 是否可编辑"""
        from fastapi import HTTPException
        if status_val not in ("draft", "paused"):
            raise HTTPException(
                400,
                f"Workflow 状态为 '{status_val}'，仅 draft/paused 状态可编辑"
            )
