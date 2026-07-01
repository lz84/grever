# -*- coding: utf-8 -*-
"""Scenario instantiate — 辅助函数"""
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text


def _evaluate_condition_preview(condition_type: Optional[str], condition_data: Optional[str]) -> bool:
    """预览阶段判断任务是否应创建"""
    if not condition_type or condition_type == 'none':
        return True
    if condition_type == 'auto_eval':
        return True
    return False


EXECUTOR_REQUIRES_HITL = frozenset({'human', 'ai_approval', 'ai_data'})
EXECUTOR_TO_INPUT_TYPE = {
    'human': 'data_entry',
    'ai_approval': 'approval',
    'ai_data': 'data_entry',
}


def _determine_executor_behavior(executor_type: Optional[str]) -> Tuple[str, bool]:
    """根据 executor_type 返回 (task_status, needs_hitl_request)"""
    if executor_type in EXECUTOR_REQUIRES_HITL:
        return ('paused', True)
    return ('todo', False)


def _build_context_md(scenario_id: str, scenario_name: str, conn) -> str:
    """构建 context_md"""
    rows = conn.execute(
        text("SELECT name, description FROM scenario_tasks "
             "WHERE scenario_id = :sid AND deleted = 0 ORDER BY display_order"),
        {"sid": scenario_id}
    ).fetchall()
    if not rows:
        return ""
    lines = [f"## 场景任务清单: {scenario_name}"]
    for r in rows:
        lines.append(f"- **{r[0]}**: {r[1] or ''}")
    return "\n".join(lines)


def _create_hitl_request(conn, task_id: str, goal_id: str, project_id: str) -> None:
    """为 task 创建 human_input_request（幂等）"""
    import uuid
    from datetime import datetime
    existing = conn.execute(
        text("SELECT id FROM human_input_requests WHERE task_id = :tid AND status IN ('pending','submitted')"),
        {"tid": task_id}
    ).fetchone()
    if existing:
        return
    hir_id = f"hir-{uuid.uuid4().hex[:12]}"
    now = datetime.now().isoformat()
    conn.execute(
        text("INSERT INTO human_input_requests (id,task_id,goal_id,project_id,request_type,status,created_at) "
             "VALUES (:id,:tid,:gid,:pid,:rtype,'pending',:now)"),
        {"id": hir_id, "tid": task_id, "gid": goal_id, "pid": project_id, "rtype": "scenario_instance", "now": now}
    )


def _resolve_industry_dimension(tag_ids: List[str], conn) -> Dict[str, List[str]]:
    """从 industry_tags 表解析维度标签"""
    if not tag_ids:
        return {}
    rows = conn.execute(
        text("SELECT tag_name FROM industry_tags WHERE id IN :ids AND deleted = 0"),
        {"ids": tuple(tag_ids)}
    ).fetchall()
    dim_rows = conn.execute(
        text("SELECT DISTINCT dimension FROM industry_tags "
             "WHERE id IN :ids AND dimension IS NOT NULL AND dimension != ''"),
        {"ids": tuple(tag_ids)}
    ).fetchall()
    return {"dimensions": [r[0] for r in dim_rows], "tags": [r[0] for r in rows]}


def _should_create_task(condition_type: Optional[str]) -> bool:
    """判断任务是否应被创建"""
    if not condition_type or condition_type == 'none':
        return True
    if condition_type in ('auto_eval', 'human_decision', 'human_input'):
        return False
    return True
