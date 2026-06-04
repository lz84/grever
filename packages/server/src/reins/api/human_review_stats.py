"""Human Review API: stats & pending endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from reins.common.database import get_db
from .human_review_logic import _to_iso
from .human_review_models import HumanReviewStats, PendingItem, PendingResponse

_PRIORITY_MAP = {1: "low", 2: "medium", 3: "high"}

def _priority_str(p) -> Optional[str]:
    """Convert DB integer priority to string label."""
    if p is None:
        return None
    if isinstance(p, str):
        return p
    return _PRIORITY_MAP.get(int(p), "medium")

router = APIRouter()

@router.get("/stats", response_model=HumanReviewStats)
def get_human_review_stats(db: Session = Depends(get_db)):
    """获取人类审核统计信息"""
    try:
        disputed_result = db.execute(text("SELECT COUNT(*) FROM tasks WHERE status = 'disputed'")).fetchone()
        disputed_count = disputed_result[0] if disputed_result else 0

        waiting_human_result = db.execute(text("SELECT COUNT(*) FROM tasks WHERE status = 'waiting_human'")).fetchone()
        waiting_human_count = waiting_human_result[0] if waiting_human_result else 0

        pending_result = db.execute(text("SELECT COUNT(*) FROM human_input_requests WHERE status = 'pending'")).fetchone()
        pending_count = pending_result[0] if pending_result else 0

        total = disputed_count + waiting_human_count + pending_count

        recent_items: list = []
        disputed_tasks = db.execute(text("""
            SELECT t.id, t.title, t.description, t.status, t.priority, p.goal_id,
                   t.project_id, t.verification_cycle, t.created_at, t.updated_at
            FROM tasks t LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.status = 'disputed'
            ORDER BY t.created_at DESC LIMIT 5
        """)).fetchall()

        for task in disputed_tasks:
            recent_items.append({
                "id": task.id, "type": "disputed", "title": task.title or f"Disputed Task {task.id}",
                "description": task.description, "status": task.status, "priority": _priority_str(task.priority),
                "created_at": _to_iso(task.created_at), "updated_at": _to_iso(task.updated_at) or None,
                "task_id": task.id, "goal_id": task.goal_id, "project_id": task.project_id,
                "verification_cycle": task.verification_cycle, "metadata": {"task_type": "disputed_task"}
            })

        waiting_tasks = db.execute(text("""
            SELECT t.id, t.title, t.description, t.status, t.priority, p.goal_id,
                   t.project_id, t.verification_cycle, t.created_at, t.updated_at
            FROM tasks t LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.status = 'waiting_human'
            ORDER BY t.created_at DESC LIMIT 5
        """)).fetchall()

        for task in waiting_tasks:
            recent_items.append({
                "id": task.id, "type": "waiting_human", "title": task.title or f"Waiting Human Task {task.id}",
                "description": task.description, "status": task.status, "priority": _priority_str(task.priority),
                "created_at": _to_iso(task.created_at), "updated_at": _to_iso(task.updated_at) or None,
                "task_id": task.id, "goal_id": task.goal_id, "project_id": task.project_id,
                "verification_cycle": task.verification_cycle, "metadata": {"task_type": "waiting_human_task"}
            })

        pending_requests = db.execute(text("""
            SELECT id, task_id, title, description, input_type, status, created_at, updated_at
            FROM human_input_requests WHERE status = 'pending'
            ORDER BY created_at DESC LIMIT 5
        """)).fetchall()

        for req in pending_requests:
            recent_items.append({
                "id": req.id, "type": "pending_assist", "title": req.title or f"Human Input Request {req.id}",
                "description": req.description, "status": req.status, "input_type": req.input_type,
                "created_at": _to_iso(req.created_at), "updated_at": _to_iso(req.updated_at) or None,
                "task_id": req.task_id, "metadata": {"request_type": "human_input_request"}
            })

        recent_items.sort(key=lambda x: x["created_at"], reverse=True)
        recent_items = recent_items[:5]

        return HumanReviewStats(
            disputed_count=disputed_count, waiting_human_count=waiting_human_count,
            pending_count=pending_count, total=total, recent_pending=recent_items
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取人类审核统计失败: {str(e)}")

@router.get("/pending", response_model=PendingResponse)
def get_human_review_pending(
    type: str = Query(default="all"),
    priority: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    db: Session = Depends(get_db)
):
    """获取待处理项列表"""
    try:
        if type not in ["all", "disputed", "waiting", "assist"]:
            raise HTTPException(status_code=400, detail="type must be one of: all, disputed, waiting, assist")
        if priority and priority not in ["low", "medium", "high"]:
            raise HTTPException(status_code=400, detail="priority must be one of: low, medium, high")
        valid_sort_fields = ["created_at", "updated_at", "priority", "status"]
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"
        order_desc = sort_order.lower() == 'desc'

        all_items: List[PendingItem] = []

        if type in ["all", "disputed"]:
            disputed_sql = text("""
                SELECT t.id, t.title, t.description, t.status, t.priority, p.goal_id,
                       t.project_id, t.verification_cycle, t.created_at, t.updated_at
                FROM tasks t LEFT JOIN projects p ON t.project_id = p.id
                WHERE t.status = 'disputed'
            """)
            if priority:
                disputed_sql = text("""
                    SELECT t.id, t.title, t.description, t.status, t.priority, p.goal_id,
                           t.project_id, t.verification_cycle, t.created_at, t.updated_at
                    FROM tasks t LEFT JOIN projects p ON t.project_id = p.id
                    WHERE t.status = 'disputed' AND t.priority = :priority
                """)
            disputed_rows = db.execute(disputed_sql, {"priority": priority} if priority else {}).fetchall()
            for task in disputed_rows:
                all_items.append(PendingItem(
                    id=task.id, type="disputed", title=task.title or f"Disputed Task {task.id}",
                    description=task.description, status=task.status, priority=_priority_str(task.priority),
                    created_at=_to_iso(task.created_at),
                    updated_at=_to_iso(task.updated_at) or None, task_id=task.id,
                    goal_id=task.goal_id, project_id=task.project_id,
                    verification_cycle=task.verification_cycle, metadata={"task_type": "disputed_task"}
                ))

        if type in ["all", "waiting"]:
            waiting_sql = text("""
                SELECT t.id, t.title, t.description, t.status, t.priority, p.goal_id,
                       t.project_id, t.verification_cycle, t.created_at, t.updated_at
                FROM tasks t LEFT JOIN projects p ON t.project_id = p.id
                WHERE t.status = 'waiting_human'
            """)
            if priority:
                waiting_sql = text("""
                    SELECT t.id, t.title, t.description, t.status, t.priority, p.goal_id,
                           t.project_id, t.verification_cycle, t.created_at, t.updated_at
                    FROM tasks t LEFT JOIN projects p ON t.project_id = p.id
                    WHERE t.status = 'waiting_human' AND t.priority = :priority
                """)
            waiting_rows = db.execute(waiting_sql, {"priority": priority} if priority else {}).fetchall()
            for task in waiting_rows:
                all_items.append(PendingItem(
                    id=task.id, type="waiting_human", title=task.title or f"Waiting Human Task {task.id}",
                    description=task.description, status=task.status, priority=_priority_str(task.priority),
                    created_at=_to_iso(task.created_at), updated_at=_to_iso(task.updated_at) or None,
                    task_id=task.id, goal_id=task.goal_id, project_id=task.project_id,
                    verification_cycle=task.verification_cycle, metadata={"task_type": "waiting_human_task"}
                ))

        if type in ["all", "assist"]:
            assist_sql = text("""
                SELECT hir.id, hir.task_id, hir.title, hir.description, hir.input_type,
                       hir.status, hir.created_at, hir.updated_at, t.priority as priority
                FROM human_input_requests hir LEFT JOIN tasks t ON hir.task_id = t.id
                WHERE hir.status = 'pending'
            """)
            if priority:
                assist_sql = text("""
                    SELECT hir.id, hir.task_id, hir.title, hir.description, hir.input_type,
                           hir.status, hir.created_at, hir.updated_at, t.priority as priority
                    FROM human_input_requests hir LEFT JOIN tasks t ON hir.task_id = t.id
                    WHERE hir.status = 'pending' AND t.priority = :priority
                """)
            assist_rows = db.execute(assist_sql, {"priority": priority} if priority else {}).fetchall()
            for req in assist_rows:
                all_items.append(PendingItem(
                    id=req.id, type="pending_assist", title=req.title or f"Human Input Request {req.id}",
                    description=req.description, status=req.status, priority=_priority_str(req.priority),
                    created_at=_to_iso(req.created_at), updated_at=_to_iso(req.updated_at) or None,
                    task_id=req.task_id, input_type=req.input_type, metadata={"request_type": "human_input_request"}
                ))

        sort_key_map = {
            "created_at": lambda x: x.created_at or "",
            "updated_at": lambda x: x.updated_at or "",
            "priority": lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.priority, 3),
            "status": lambda x: x.status or "",
        }
        key_func = sort_key_map.get(sort_by, sort_key_map["created_at"])
        all_items.sort(key=key_func, reverse=order_desc)

        total = len(all_items)
        page = (offset // limit) + 1 if limit > 0 else 1
        paged_items = all_items[offset:offset + limit]

        return PendingResponse(items=paged_items, total=total, page=page, page_size=limit)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取待处理项失败: {str(e)}")
