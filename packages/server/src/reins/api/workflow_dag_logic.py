"""工作流 DAG 逻辑模块"""

import json
import re
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from models import Workflow
from pydantic import BaseModel, Field

class DagChange(BaseModel):
    action: str = Field(..., description="操作类型: merge/insert/delete/move/rename")
    detail: str = Field(..., description="操作详情")

def _get_workflow_dag(db: Session, workflow_id: str) -> Optional[dict]:
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        return None
    dag = json.loads(workflow.dag) if isinstance(workflow.dag, str) else (workflow.dag or {"nodes": [], "edges": []})
    return {"id": workflow.id, "name": workflow.name, "status": workflow.status, "dag": dag}

def _save_dag(db: Session, workflow_id: str, dag: dict):
    now = datetime.now().isoformat()
    db.query(Workflow).filter(Workflow.id == workflow_id).update({"dag": json.dumps(dag, ensure_ascii=False), "updated_at": now})

def _edge_src(edge: dict) -> str:
    return str(edge.get("source", edge.get("from", "")))

def _edge_tgt(edge: dict) -> str:
    return str(edge.get("target", edge.get("to", "")))

def _validate_dag(dag: dict) -> Tuple[bool, str]:
    nodes = dag.get("nodes", [])
    edges = dag.get("edges", [])
    node_ids = {n["id"] for n in nodes}
    for edge in edges:
        if _edge_src(edge) not in node_ids:
            return False, f"边引用了不存在的源节点: {_edge_src(edge)}"
        if _edge_tgt(edge) not in node_ids:
            return False, f"边引用了不存在的目标节点: {_edge_tgt(edge)}"
    adj: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
    in_degree: Dict[str, int] = {n["id"]: 0 for n in nodes}
    for edge in edges:
        src, tgt = _edge_src(edge), _edge_tgt(edge)
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
        return False, "DAG 存在循环依赖"
    return True, ""

def _sync_steps(db: Session, workflow_id: str, dag: dict) -> int:
    nodes = dag.get("nodes", [])
    now = datetime.now().isoformat()
    for i, node in enumerate(nodes):
        nid = node["id"]
        node_type = node.get("type", "execution")
        deps = json.dumps(node.get("dependencies", []), ensure_ascii=False)
        assignee = node.get("assignee", "")
        title = node.get("title", node.get("name", ""))
        desc = node.get("description", "")
        input_data = json.dumps({"node_type": node_type}, ensure_ascii=False)
        # EXCEPTION: SQLite ON CONFLICT upsert, not easily expressible in ORM
        db.execute(text("""
            INSERT INTO workflow_steps
            (id, workflow_id, name, description, status, dependencies, "order", agent_id, input_data, output_data, retry_count, max_retries, created_at, updated_at)
            VALUES (:id, :wf, :name, :desc, 'pending', :deps, :ord, :agent, :input, '{}', 0, 3, :now, :now)
            ON CONFLICT(id) DO UPDATE SET
                workflow_id = :wf, name = :name, description = :desc, status = 'pending', dependencies = :deps, "order" = :ord, agent_id = :agent, input_data = :input, updated_at = :now
        """), {"id": nid, "wf": workflow_id, "name": title, "desc": desc, "deps": deps, "ord": i, "agent": assignee, "input": input_data, "now": now})
    return len(nodes)

def _find_node(nodes: list, name: str) -> Optional[dict]:
    for n in nodes:
        if n["id"] == name:
            return n
    title_lower = name.lower()
    for n in nodes:
        title = (n.get("title") or n.get("name") or "").lower()
        if title_lower in title or title in title_lower:
            return n
    num_match = re.search(r'(?:阶段|phase)[-—]*(\d+)', name, re.IGNORECASE)
    if num_match:
        idx = int(num_match.group(1)) - 1
        if 0 <= idx < len(nodes):
            return nodes[idx]
    return None

def _parse_instruction(instruction: str, dag: dict) -> dict:
    nodes = dag.get("nodes", [])
    edges = dag.get("edges", [])
    text = instruction.lower()
    rename_patterns = [r'把(.+?)改名为?(.+)', r'将(.+?)改为(.+)', r'(.+?)改成(.+)', r'(.+?)重命名为(.+)']
    for pat in rename_patterns:
        m = re.search(pat, text)
        if m:
            old_name = m.group(1).strip()
            new_name = m.group(2).strip()
            target = _find_node(nodes, old_name)
            if target:
                return {"action": "rename", "node_id": target["id"], "new_title": new_name}
    merge_patterns = [r'把(.+?)和(.+?)合并', r'合并(.+?)和(.+)']
    for pat in merge_patterns:
        m = re.search(pat, text)
        if m:
            name_a = m.group(1).strip()
            name_b = m.group(2).strip()
            node_a = _find_node(nodes, name_a)
            node_b = _find_node(nodes, name_b)
            if node_a and node_b:
                return {"action": "merge", "source_id": node_a["id"], "target_id": node_b["id"], "new_title": f"{node_a.get('title', '')}+{node_b.get('title', '')}"}
    delete_patterns = [r'删除最后一个.*', r'去掉最后一个.*', r'删除(.+)', r'去掉(.+)']
    for pat in delete_patterns:
        m = re.search(pat, text)
        if m:
            if '最后' in text:
                target = nodes[-1] if nodes else None
            else:
                target = _find_node(nodes, m.group(1).strip())
            if target:
                return {"action": "delete", "node_id": target["id"]}
    insert_after = re.search(r'在(.+?)后面加(一个)?(.+)', text)
    if insert_after:
        ref_name = insert_after.group(1).strip()
        new_title = insert_after.group(3).strip()
        ref = _find_node(nodes, ref_name)
        if ref:
            return {"action": "insert_after", "ref_id": ref["id"], "new_title": new_title}
    insert_before = re.search(r'在(.+?)前面插(入)?(.+)', text)
    if insert_before:
        ref_name = insert_before.group(1).strip()
        new_title = insert_before.group(3).strip()
        ref = _find_node(nodes, ref_name)
        if ref:
            return {"action": "insert_before", "ref_id": ref["id"], "new_title": new_title}
    insert_any = re.search(r'加(一个)?(.+)', text)
    if insert_any:
        new_title = insert_any.group(2).strip()
        return {"action": "append", "new_title": new_title}
    move_first = re.search(r'把(.+?)移到最前面', text)
    if move_first:
        target = _find_node(nodes, move_first.group(1).strip())
        if target:
            return {"action": "move_first", "node_id": target["id"]}
    move_after = re.search(r'把(.+?)移到(.+?)后面', text)
    if move_after:
        target = _find_node(nodes, move_after.group(1).strip())
        ref = _find_node(nodes, move_after.group(2).strip())
        if target and ref:
            return {"action": "move_after", "node_id": target["id"], "ref_id": ref["id"]}
    return {"action": "unknown", "message": f"无法解析指令: {instruction}"}

def _execute_action(dag: dict, op: dict) -> Tuple[dict, List[DagChange], str]:
    action = op.get("action", "unknown")
    nodes = dag.get("nodes", [])
    edges = dag.get("edges", [])
    changes = []
    try:
        if action == "rename":
            node_id = op["node_id"]
            new_title = op["new_title"]
            for n in nodes:
                if n["id"] == node_id:
                    old_title = n.get("title", "")
                    n["title"] = new_title
                    changes.append(DagChange(action="rename", detail=f"重命名 '{old_title}' → '{new_title}'"))
                    break
        elif action == "merge":
            src_id = op["source_id"]
            tgt_id = op["target_id"]
            new_title = op.get("new_title", "合并阶段")
            src = next((n for n in nodes if n["id"] == src_id), None)
            tgt = next((n for n in nodes if n["id"] == tgt_id), None)
            if not src or not tgt:
                return dag, changes, "合并的节点不存在"
            merged_desc = f"{src.get('description', '')}\n{tgt.get('description', '')}".strip()
            merged_type = src.get("type", "execution")
            all_deps = set()
            for e in edges:
                if _edge_tgt(e) == src_id:
                    all_deps.add(_edge_src(e))
                if _edge_tgt(e) == tgt_id:
                    all_deps.add(_edge_src(e))
            successors = set()
            for e in edges:
                if _edge_src(e) == src_id:
                    successors.add(_edge_tgt(e))
                if _edge_src(e) == tgt_id:
                    successors.add(_edge_tgt(e))
            src["title"] = new_title
            src["description"] = merged_desc
            src["type"] = merged_type
            src["dependencies"] = list(all_deps - {tgt_id})
            dag["nodes"] = [n for n in nodes if n["id"] != tgt_id]
            dag["edges"] = [e for e in edges if _edge_src(e) != src_id and _edge_tgt(e) != src_id and _edge_src(e) != tgt_id and _edge_tgt(e) != tgt_id]
            for dep_id in all_deps - {tgt_id}:
                if dep_id in {n["id"] for n in dag["nodes"]}:
                    dag["edges"].append({"source": dep_id, "target": src_id})
            for suc_id in successors - {src_id, tgt_id}:
                if suc_id in {n["id"] for n in dag["nodes"]}:
                    dag["edges"].append({"source": src_id, "target": suc_id})
            changes.append(DagChange(action="merge", detail=f"合并 '{src.get('title', '')}' 和 '{tgt.get('title', '')}' → '{new_title}'"))
        elif action == "delete":
            node_id = op["node_id"]
            target = next((n for n in nodes if n["id"] == node_id), None)
            if not target:
                return dag, changes, "要删除的节点不存在"
            title = target.get("title", "")
            dag["nodes"] = [n for n in nodes if n["id"] != node_id]
            dag["edges"] = [e for e in edges if _edge_src(e) != node_id and _edge_tgt(e) != node_id]
            changes.append(DagChange(action="delete", detail=f"删除节点 '{title}'"))
        elif action in ("insert_after", "insert_before", "append"):
            new_title = op["new_title"]
            new_id = f"step-{uuid.uuid4().hex[:8]}"
            if action == "append":
                new_node = {"id": new_id, "title": new_title, "type": "execution", "description": "", "dependencies": []}
                if nodes:
                    new_node["dependencies"] = [nodes[-1]["id"]]
                    dag["edges"].append({"source": nodes[-1]["id"], "target": new_id})
                dag["nodes"].append(new_node)
                changes.append(DagChange(action="insert", detail=f"追加节点 '{new_title}'"))
            else:
                ref_id = op["ref_id"]
                ref_idx = next((i for i, n in enumerate(nodes) if n["id"] == ref_id), None)
                if ref_idx is None:
                    return dag, changes, "参考节点不存在"
                new_node = {"id": new_id, "title": new_title, "type": "execution", "description": "", "dependencies": []}
                if action == "insert_after":
                    new_node["dependencies"] = [ref_id]
                    dag["edges"].append({"source": ref_id, "target": new_id})
                    for e in dag["edges"]:
                        if _edge_src(e) == ref_id and _edge_tgt(e) != new_id:
                            e["source"] = new_id
                    dag["nodes"].insert(ref_idx + 1, new_node)
                    changes.append(DagChange(action="insert", detail=f"在 '{nodes[ref_idx].get('title', '')}' 后面插入 '{new_title}'"))
                elif action == "insert_before":
                    ref_deps = [e for e in edges if _edge_tgt(e) == ref_id]
                    new_node["dependencies"] = [_edge_src(e) for e in ref_deps]
                    for e in dag["edges"]:
                        if _edge_tgt(e) == ref_id and _edge_src(e) != new_id:
                            e["target"] = new_id
                    dag["edges"].append({"source": new_id, "target": ref_id})
                    dag["nodes"].insert(ref_idx, new_node)
                    changes.append(DagChange(action="insert", detail=f"在 '{nodes[ref_idx + 1].get('title', '')}' 前面插入 '{new_title}'"))
        elif action in ("move_first", "move_after"):
            node_id = op["node_id"]
            target = next((n for n in nodes if n["id"] == node_id), None)
            if not target:
                return dag, changes, "要移动的节点不存在"
            title = target.get("title", "")
            dag["nodes"] = [n for n in nodes if n["id"] != node_id]
            dag["edges"] = [e for e in edges if _edge_src(e) != node_id and _edge_tgt(e) != node_id]
            if action == "move_first":
                dag["nodes"].insert(0, target)
                changes.append(DagChange(action="move", detail=f"将 '{title}' 移到最前面"))
            elif action == "move_after":
                ref_id = op["ref_id"]
                ref_idx = next((i for i, n in enumerate(dag["nodes"]) if n["id"] == ref_id), None)
                if ref_idx is not None:
                    dag["nodes"].insert(ref_idx + 1, target)
                    target["dependencies"] = [ref_id]
                    dag["edges"].append({"source": ref_id, "target": node_id})
                    changes.append(DagChange(action="move", detail=f"将 '{title}' 移到 '{dag['nodes'][ref_idx].get('title', '')}' 后面"))
        else:
            return dag, changes, op.get("message", "无法解析指令")
    except Exception as e:
        return dag, changes, str(e)
    return dag, changes, ""