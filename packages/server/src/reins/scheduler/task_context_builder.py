"""
任务执行上下文统一构建器 — Sprint 84

职责：
1. 从 DB 构建完整的 目标→工程→任务 三级上下文
2. 查询各级附件信息，生成完整下载 URL
3. 输出统一的 Markdown 格式 prompt

统一后所有派发路径（心跳/CLI/注入器）都用这个函数。
"""

import json
from loguru import logger
import os
from typing import Optional
from sqlalchemy import text

_DEFAULT_BASE_URL = os.environ.get("GREVER_BASE_URL", "http://127.0.0.1:8097")

def build_task_execution_context(
    task_id: str,
    db,
    include_attachments: bool = True,
    include_cognitions: bool = False,
    base_url: Optional[str] = None,
) -> dict:
    """
    构建任务执行的完整上下文。

    db: DatabaseManager 实例（有 .engine.connect() 方法）或已有 connection
    """
    ctx = {
        "task": {},
        "project": {},
        "goal": {},
        "attachments": {"goal": [], "project": [], "task": []},
        "dependencies": [],
    }

    # 支持两种 db 参数：DatabaseManager（有 .engine.connect()）或已有 connection
    if hasattr(db, 'engine'):
        conn = db.engine.connect()
        close_conn = True
    else:
        conn = db
        close_conn = False

    try:
        row = conn.execute(text("""
            SELECT
                t.id as task_id, t.title as task_title, t.description as task_description,
                t.status as task_status, t.priority as task_priority,
                t.assigned_agent as task_assigned_agent,
                t.acceptance_criteria as task_acceptance_criteria,
                t.delivery_criteria as task_delivery_criteria,
                t.depends_on as task_depends_on,
                t.context_md as task_context_md,
                p.id as project_id, p.name as project_name, p.description as project_description,
                p.status as project_status,
                g.id as goal_id, g.title as goal_title, g.description as goal_description,
                g.status as goal_status, g.mode as goal_mode
            FROM tasks t
            LEFT JOIN projects p ON t.project_id = p.id
            LEFT JOIN goals g ON p.goal_id = g.id
            WHERE t.id = :task_id
        """), {"task_id": task_id}).fetchone()

        if not row:
            return ctx

        def _parse_json_field(val):
            if not val:
                return []
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return []
            return val if isinstance(val, list) else []

        ctx["task"] = {
            "id": row.task_id,
            "title": row.task_title or "",
            "description": row.task_description or "",
            "status": row.task_status or "todo",
            "priority": row.task_priority or "medium",
            "assigned_agent": row.task_assigned_agent,
            "acceptance_criteria": _parse_json_field(row.task_acceptance_criteria),
            "delivery_criteria": _parse_json_field(row.task_delivery_criteria),
            "context_md": row.task_context_md or "",
        }

        if row.project_id:
            ctx["project"] = {
                "id": row.project_id,
                "name": row.project_name or "",
                "description": row.project_description or "",
                "status": row.project_status or "active",
            }

        if row.goal_id:
            ctx["goal"] = {
                "id": row.goal_id,
                "title": row.goal_title or "",
                "description": row.goal_description or "",
                "status": row.goal_status or "active",
                "mode": row.goal_mode or "engineering",
            }

        deps_raw = _parse_json_field(row.task_depends_on)
        if deps_raw:
            placeholders = ",".join([f":dep{i}" for i in range(len(deps_raw))])
            dep_rows = conn.execute(text(
                f"SELECT id, title, status FROM tasks WHERE id IN ({placeholders})"
            ), {f"dep{i}": d for i, d in enumerate(deps_raw)}).fetchall()
            ctx["dependencies"] = [
                {"id": r.id, "title": r.title, "status": r.status} for r in dep_rows
            ]

        if include_attachments:
            _fetch_attachments(conn, ctx, base_url=_get_base_url(base_url))

        ctx["prompt"] = _build_unified_prompt(ctx)
    finally:
        if close_conn:
            conn.close()

    return ctx

def _get_base_url(base_url: Optional[str] = None) -> str:
    return base_url.rstrip("/") if base_url else _DEFAULT_BASE_URL

def _fetch_attachments(conn, ctx: dict, base_url: str):
    """查询目标/工程/任务的附件列表，包含完整下载 URL"""

    def _get_attachments(entity_type, entity_id):
        if not entity_id:
            return []
        try:
            rows = conn.execute(text("""
                SELECT a.id, a.filename, a.mime_type, a.file_size, a.created_at
                FROM attachments a
                JOIN attachment_links l ON a.id = l.attachment_id
                WHERE l.entity_type = :et AND l.entity_id = :eid
                ORDER BY a.created_at ASC
            """), {"et": entity_type, "eid": entity_id}).fetchall()
            return [{
                "id": r.id,
                "filename": r.filename,
                "mime_type": r.mime_type,
                "file_size": r.file_size,
                "download_url": f"{base_url}/api/v1/attachments/{r.id}/download",
                "created_at": str(r.created_at) if r.created_at else "",
            } for r in rows]
        except Exception:
            return []

    ctx["attachments"]["goal"] = _get_attachments("goal", ctx["goal"].get("id"))
    ctx["attachments"]["project"] = _get_attachments("project", ctx["project"].get("id"))
    ctx["attachments"]["task"] = _get_attachments("task", ctx["task"].get("id"))

def _build_unified_prompt(ctx: dict) -> str:
    """构建统一的 Markdown 格式 prompt"""
    lines = []

    # ── Level 0: 目标 ──
    goal = ctx["goal"]
    if goal.get("id"):
        lines.append("# 🎯 目标（Goal）")
        lines.append(f"## {goal['title']}")
        if goal.get("description"):
            lines.append(goal["description"])
        lines.append(f"- 目标ID：`{goal['id']}`")
        if goal.get("status"):
            lines.append(f"- 状态：{goal['status']}")
        if goal.get("mode"):
            mode_map = {"engineering": "工程模式", "research": "研究模式"}
            lines.append(f"- 模式：{mode_map.get(goal['mode'], goal['mode'])}")

        goal_atts = ctx["attachments"]["goal"]
        if goal_atts:
            lines.append(f"- 附件（{len(goal_atts)}个）：")
            for att in goal_atts:
                size_kb = att["file_size"] / 1024 if att["file_size"] else 0
                lines.append(f"  - 📎 [{att['filename']}]({att['download_url']}) ({size_kb:.1f} KB)")
        lines.append("")

    # ── Level 1: 工程 ──
    project = ctx["project"]
    if project.get("id"):
        lines.append("# 📁 工程（Project）")
        lines.append(f"## {project['name']}")
        if project.get("description"):
            lines.append(project["description"])
        lines.append(f"- 工程ID：`{project['id']}`")
        if project.get("status"):
            lines.append(f"- 状态：{project['status']}")

        proj_atts = ctx["attachments"]["project"]
        if proj_atts:
            lines.append(f"- 附件（{len(proj_atts)}个）：")
            for att in proj_atts:
                size_kb = att["file_size"] / 1024 if att["file_size"] else 0
                lines.append(f"  - 📎 [{att['filename']}]({att['download_url']}) ({size_kb:.1f} KB)")
        lines.append("")

    # ── Level 2: 任务 ──
    task = ctx["task"]
    lines.append("# 📋 当前任务（Task）")
    lines.append(f"## {task.get('title', '')}")
    if task.get("description"):
        lines.append(task["description"])
    lines.append(f"- 任务ID：`{task['id']}`")
    if task.get("priority"):
        lines.append(f"- 优先级：{task['priority']}")
    if task.get("status"):
        lines.append(f"- 状态：{task['status']}")

    context_md = task.get("context_md", "")
    if context_md:
        lines.append("")
        lines.append("### 🧭 执行者上下文")
        lines.append(context_md)

    # ── 交付标准（执行者看）──
    delivery = task.get("delivery_criteria", [])
    if delivery:
        lines.append("")
        # 支持 {"title": "...", "criteria": [...]} 或 直接列表
        if isinstance(delivery, dict):
            title = delivery.get("title", "交付标准")
            criteria = delivery.get("criteria", [])
        else:
            title = "交付标准"
            criteria = delivery
        if criteria:
            lines.append(f"### 📦 {title}")
            lines.append("*以下全部自测通过后，才可标记任务完成：*")
            for i, item in enumerate(criteria, 1):
                if isinstance(item, dict):
                    name = item.get("name", f"检查{i}")
                    desc = item.get("desc", "")
                    lines.append(f"- [ ] {name}: {desc}")
                else:
                    lines.append(f"- [ ] {item}")

    # ── 验收标准（验证者看）──
    acceptance = task.get("acceptance_criteria", [])
    if acceptance:
        # 支持 {'criteria': [...]} 或直接列表
        if isinstance(acceptance, dict):
            criteria_list = acceptance.get("criteria", [])
        else:
            criteria_list = acceptance
        if criteria_list:
            lines.append("")
            lines.append("### ✅ 验收标准")
            for i, criterion in enumerate(criteria_list, 1):
                if isinstance(criterion, dict):
                    lines.append(f"{i}. [{criterion.get('type', '')}] {criterion.get('desc', criterion.get('description', str(criterion)))}")
                else:
                    lines.append(f"{i}. {criterion}")

    deps = ctx["dependencies"]
    if deps:
        lines.append("")
        lines.append("### 🔗 前置依赖")
        for dep in deps:
            status_emoji = {"done": "✅", "failed": "❌", "in_progress": "⏳"}.get(dep["status"], "⬜")
            lines.append(f"- {status_emoji} `{dep['id']}` — {dep['title']} ({dep['status']})")

    task_atts = ctx["attachments"]["task"]
    if task_atts:
        lines.append("")
        lines.append("### 📎 任务附件")
        for att in task_atts:
            size_kb = att["file_size"] / 1024 if att["file_size"] else 0
            lines.append(f"- 📎 [{att['filename']}]({att['download_url']}) ({size_kb:.1f} KB)")

    lines.append("")
    lines.append("/// 任务结束 ///")

    return "\n".join(lines)
