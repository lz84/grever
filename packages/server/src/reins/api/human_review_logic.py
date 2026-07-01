"""人工裁决逻辑模块"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import uuid
import json

from models.task import Task
from models.human_input import HumanInputRequest
from models.goal import Goal
from models.project import Project

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
        # Use ORM to query task with LEFT JOIN projects
        task_obj = db.query(Task).filter(Task.id == task_id).first()
        if not task_obj:
            return None
        project_obj = db.query(Project).filter(Project.id == task_obj.project_id).first()
        goal_id = project_obj.goal_id if project_obj else None
        return {
            "id": task_obj.id, "title": task_obj.title, "description": task_obj.description,
            "status": task_obj.status, "priority": task_obj.priority, "goal_id": goal_id,
            "project_id": task_obj.project_id, "verification_cycle": task_obj.verification_cycle,
            "created_at": _to_iso(datetime.utcfromtimestamp(task_obj.created_at)) if task_obj.created_at else None,
            "updated_at": _to_iso(datetime.utcfromtimestamp(task_obj.updated_at)) if task_obj.updated_at else None
        }
    except Exception:
        return None

def _get_human_input_request(db: Session, input_id: str) -> Optional[Dict[str, Any]]:
    """获取人类输入请求"""
    try:
        req = db.query(HumanInputRequest).filter(HumanInputRequest.id == input_id).first()
        if not req:
            return None
        context = None
        if req.context:
            try:
                context = json.loads(req.context) if isinstance(req.context, str) else req.context
            except (json.JSONDecodeError, TypeError):
                context = None
        return {
            "id": req.id, "task_id": req.task_id, "title": req.title,
            "description": req.description, "input_type": req.input_type,
            "status": req.status, "created_at": _to_iso(req.created_at) or None,
            "updated_at": _to_iso(req.updated_at) or None,
            "context": context
        }
    except Exception:
        return None

def _process_task_ruling(db: Session, task_id: str, ruling: str, action: str) -> Dict[str, Any]:
    """处理任务裁决"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError(f"任务不存在: {task_id}")

    now = datetime.now()
    try:
        comment_id = f"cmtr-{uuid.uuid4().hex[:8]}"
        # Note: task_comments table may not have an ORM model, keeping raw INSERT
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
        db.query(Task).filter(Task.id == task_id).update(
            {"status": "done", "completed_at": now, "updated_at": now},
            synchronize_session="fetch"
        )
    elif action in ("in_progress", "request_changes"):
        # 要求修改 → 退回 todo，清验证周期
        new_status = "todo"
        db.query(Task).filter(Task.id == task_id).update(
            {"status": "todo", "verification_cycle": 0,
             "error_message": None, "started_at": None, "completed_at": None,
             "updated_at": now},
            synchronize_session="fetch"
        )
    elif action == "verifying":
        new_status = "verifying"
        db.query(Task).filter(Task.id == task_id).update(
            {"status": "verifying", "updated_at": now},
            synchronize_session="fetch"
        )
    elif action in ("reject", "failed"):
        new_status = "failed"
        db.query(Task).filter(Task.id == task_id).update(
            {"status": "failed", "updated_at": now},
            synchronize_session="fetch"
        )
    elif action == "review_needed":
        new_status = "review_needed"
        db.query(Task).filter(Task.id == task_id).update(
            {"status": "review_needed", "updated_at": now},
            synchronize_session="fetch"
        )
    else:
        new_status = task.status
        db.query(Task).filter(Task.id == task_id).update(
            {"updated_at": now},
            synchronize_session="fetch"
        )

    if task.status == "waiting_human":
        db.query(HumanInputRequest).filter(
            HumanInputRequest.task_id == task_id,
            HumanInputRequest.status == "pending"
        ).update(
            {"status": "submitted" if action in ["done", "in_progress", "verifying"] else "rejected",
             "submitted_by": "human_operator", "submitted_at": now, "updated_at": now},
            synchronize_session="fetch"
        )

    db.commit()
    return {"message": f"Task {task_id} ruled successfully with action {action}", "new_status": new_status}

def _process_human_input_ruling(db: Session, input_id: str, ruling: str, action: str) -> Dict[str, Any]:
    """处理人类输入请求裁决"""
    req = db.query(HumanInputRequest).filter(HumanInputRequest.id == input_id).first()
    if not req:
        raise ValueError(f"人类输入请求不存在: {input_id}")

    task_id = req.task_id
    now = datetime.now()
    new_status = "submitted" if action in ["done", "approve", "in_progress", "verifying"] else "rejected"

    db.query(HumanInputRequest).filter(HumanInputRequest.id == input_id).update(
        {"status": new_status, "input_data": json.dumps({"ruling": ruling, "action": action}),
         "submitted_by": "human_operator", "submitted_at": now, "updated_at": now},
        synchronize_session="fetch"
    )

    if new_status == "submitted" and task_id:
        try:
            comment_id = f"cmtr-{uuid.uuid4().hex[:8]}"
            # Note: task_comments table may not have an ORM model, keeping raw INSERT
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
            db.query(Task).filter(Task.id == task_id).update(
                {"status": "done", "completed_at": now, "updated_at": now},
                synchronize_session="fetch"
            )
        elif action == "in_progress":
            db.query(Task).filter(Task.id == task_id).update(
                {"status": "in_progress", "updated_at": now},
                synchronize_session="fetch"
            )
        elif action == "verifying":
            db.query(Task).filter(Task.id == task_id).update(
                {"status": "verifying", "updated_at": now},
                synchronize_session="fetch"
            )
        else:
            db.query(Task).filter(Task.id == task_id).update(
                {"status": "done", "completed_at": now, "updated_at": now},
                synchronize_session="fetch"
            )

    db.commit()
    return {"message": f"Human input request {input_id} ruled successfully with action {action}", "new_status": new_status}
