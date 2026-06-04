"""人工裁决逻辑模块"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
import json

def _get_db_engine():
    """获取数据库引擎"""
    from reins.common.database import get_db_manager
    return get_db_manager().engine

def _to_iso(val) -> str:
    """安全地将 datetime 或 string 转换为 ISO 格式字符串"""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    return val.isoformat()

def _get_task_with_human_input(db: Session, task_id: str) -> Optional[Dict[str, Any]]:
    """获取任务及其关联的人类输入请求"""
    try:
        task = db.execute(text("""
            SELECT t.id, t.title, t.description, t.status, t.priority, p.goal_id,
                   t.project_id, t.verification_cycle, t.created_at, t.updated_at
            FROM tasks t
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.id = :task_id
        """), {"task_id": task_id}).fetchone()
        if not task:
            return None
        return {
            "id": task.id, "title": task.title, "description": task.description,
            "status": task.status, "priority": task.priority, "goal_id": task.goal_id,
            "project_id": task.project_id, "verification_cycle": task.verification_cycle,
            "created_at": _to_iso(task.created_at) or None,
            "updated_at": _to_iso(task.updated_at) or None
        }
    except Exception:
        return None

def _get_human_input_request(db: Session, input_id: str) -> Optional[Dict[str, Any]]:
    """获取人类输入请求"""
    try:
        req = db.execute(text("""
            SELECT id, task_id, title, description, input_type, status,
                   created_at, updated_at, context
            FROM human_input_requests
            WHERE id = :input_id
        """), {"input_id": input_id}).fetchone()
        if not req:
            return None
        return {
            "id": req.id, "task_id": req.task_id, "title": req.title,
            "description": req.description, "input_type": req.input_type,
            "status": req.status, "created_at": _to_iso(req.created_at) or None,
            "updated_at": _to_iso(req.updated_at) or None,
            "context": json.loads(req.context) if req.context else None
        }
    except Exception:
        return None

def _process_task_ruling(db: Session, task_id: str, ruling: str, action: str) -> Dict[str, Any]:
    """处理任务裁决"""
    task = db.execute(text("SELECT status, title FROM tasks WHERE id = :id"), {"id": task_id}).fetchone()
    if not task:
        raise ValueError(f"任务不存在: {task_id}")

    now = datetime.now()
    try:
        comment_id = f"cmtr-{uuid.uuid4().hex[:8]}"
        db.execute(text("""
            INSERT INTO task_comments
            (id, task_id, author, author_role, type, content, metadata, created_at, updated_at)
            VALUES (:id, :task_id, :author, :author_role, :type, :content, :metadata, :created_at, :updated_at)
        """), {
            "id": comment_id, "task_id": task_id, "author": "human",
            "author_role": "human_operator", "type": "human_ruling",
            "content": f"Human Ruling: {ruling}",
            "metadata": json.dumps({"ruling_action": action, "ruling_text": ruling}),
            "created_at": now, "updated_at": now
        })
    except Exception:
        pass

    new_status = None
    if action in ("done", "approve"):
        new_status = "done"
        db.execute(text("""
            UPDATE tasks SET status = 'done', completed_at = :completed_at, updated_at = :updated_at WHERE id = :task_id
        """), {"task_id": task_id, "completed_at": now, "updated_at": now})
    elif action in ("in_progress", "request_changes"):
        # 要求修改 → 退回 todo，清验证周期
        new_status = "todo"
        db.execute(text("""
            UPDATE tasks SET status = 'todo', verification_cycle = 0,
                error_message = NULL, started_at = NULL, completed_at = NULL,
                updated_at = :updated_at WHERE id = :task_id
        """), {"task_id": task_id, "updated_at": now})
    elif action == "verifying":
        new_status = "verifying"
        db.execute(text("UPDATE tasks SET status = 'verifying', updated_at = :updated_at WHERE id = :task_id"), {"task_id": task_id, "updated_at": now})
    elif action in ("reject", "failed"):
        new_status = "failed"
        db.execute(text("""
            UPDATE tasks SET status = 'failed', updated_at = :updated_at WHERE id = :task_id
        """), {"task_id": task_id, "updated_at": now})
    elif action == "review_needed":
        new_status = "review_needed"
        db.execute(text("UPDATE tasks SET status = 'review_needed', updated_at = :updated_at WHERE id = :task_id"), {"task_id": task_id, "updated_at": now})
    else:
        new_status = task.status
        db.execute(text("UPDATE tasks SET updated_at = :updated_at WHERE id = :task_id"), {"task_id": task_id, "updated_at": now})

    if task.status == "waiting_human":
        db.execute(text("""
            UPDATE human_input_requests SET status = :new_status, submitted_by = 'human_operator', submitted_at = :submitted_at, updated_at = :updated_at
            WHERE task_id = :task_id AND status = 'pending'
        """), {
            "task_id": task_id,
            "new_status": "submitted" if action in ["done", "in_progress", "verifying"] else "rejected",
            "submitted_at": now, "updated_at": now
        })

    db.commit()
    return {"message": f"Task {task_id} ruled successfully with action {action}", "new_status": new_status}

def _process_human_input_ruling(db: Session, input_id: str, ruling: str, action: str) -> Dict[str, Any]:
    """处理人类输入请求裁决"""
    req = db.execute(text("SELECT task_id, status FROM human_input_requests WHERE id = :id"), {"id": input_id}).fetchone()
    if not req:
        raise ValueError(f"人类输入请求不存在: {input_id}")

    task_id = req.task_id
    now = datetime.now()
    new_status = "submitted" if action in ["done", "approve", "in_progress", "verifying"] else "rejected"

    db.execute(text("""
        UPDATE human_input_requests SET status = :new_status, input_data = :input_data, submitted_by = 'human_operator', submitted_at = :submitted_at, updated_at = :updated_at
        WHERE id = :input_id
    """), {
        "input_id": input_id, "new_status": new_status,
        "input_data": json.dumps({"ruling": ruling, "action": action}),
        "submitted_at": now, "updated_at": now
    })

    if new_status == "submitted" and task_id:
        try:
            comment_id = f"cmtr-{uuid.uuid4().hex[:8]}"
            db.execute(text("""
                INSERT INTO task_comments (id, task_id, author, author_role, type, content, metadata, created_at, updated_at)
                VALUES (:id, :task_id, :author, :author_role, :type, :content, :metadata, :created_at, :updated_at)
            """), {
                "id": comment_id, "task_id": task_id, "author": "human",
                "author_role": "human_operator", "type": "human_ruling",
                "content": f"Human Input Approved: {ruling}",
                "metadata": json.dumps({"ruling_action": action, "input_id": input_id}),
                "created_at": now, "updated_at": now
            })
        except Exception:
            pass

        if action == "done":
            db.execute(text("UPDATE tasks SET status = 'done', completed_at = :completed_at, updated_at = :updated_at WHERE id = :task_id"), {"task_id": task_id, "completed_at": now, "updated_at": now})
        elif action == "in_progress":
            db.execute(text("UPDATE tasks SET status = 'in_progress', updated_at = :updated_at WHERE id = :task_id"), {"task_id": task_id, "updated_at": now})
        elif action == "verifying":
            db.execute(text("UPDATE tasks SET status = 'verifying', updated_at = :updated_at WHERE id = :task_id"), {"task_id": task_id, "updated_at": now})
        else:
            db.execute(text("UPDATE tasks SET status = 'done', completed_at = :completed_at, updated_at = :updated_at WHERE id = :task_id"), {"task_id": task_id, "completed_at": now, "updated_at": now})

    db.commit()
    return {"message": f"Human input request {input_id} ruled successfully with action {action}", "new_status": new_status}