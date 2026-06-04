"""人类输入 API - 统计端点"""
from loguru import logger
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from reins.common.database import get_db
from reins.api.human_input_models import HumanReviewStats

# 使用独立的 prefix，避免与其他子模块的 /stats 冲突
router = APIRouter(tags=["human-input"])

@router.get("/stats")
def get_human_input_stats(time_range: str = Query("week", description="统计范围: day, week, month"), db: Session = Depends(get_db)):
    """
    获取人类输入统计数据

    GET /api/v1/human-input/stats?range=week
    """
    try:
        date_filter_map = {
            "day": "date('now', '-1 day')",
            "week": "date('now', '-7 days')",
            "month": "date('now', '-30 days')",
        }
        date_filter = date_filter_map.get(time_range, "date('now', '-7 days')")

        # Total counts
        total_result = db.execute(text("SELECT COUNT(*) FROM human_input_requests")).fetchone()
        total = total_result[0] if total_result else 0

        pending_result = db.execute(text("SELECT COUNT(*) FROM human_input_requests WHERE status = 'pending'")).fetchone()
        pending = pending_result[0] if pending_result else 0

        submitted_result = db.execute(text("SELECT COUNT(*) FROM human_input_requests WHERE status = 'submitted'")).fetchone()
        submitted = submitted_result[0] if submitted_result else 0

        rejected_result = db.execute(text("SELECT COUNT(*) FROM human_input_requests WHERE status = 'rejected'")).fetchone()
        rejected = rejected_result[0] if rejected_result else 0

        # By type
        by_type_result = db.execute(text("""
            SELECT input_type, COUNT(*) as cnt
            FROM human_input_requests
            GROUP BY input_type
        """)).fetchall()
        by_type = {row[0]: row[1] for row in by_type_result}

        # By priority (if priority field exists)
        by_priority = {}
        try:
            priority_result = db.execute(text("""
                SELECT COALESCE(priority, 'none'), COUNT(*) as cnt
                FROM human_input_requests
                GROUP BY COALESCE(priority, 'none')
            """)).fetchall()
            by_priority = {row[0]: row[1] for row in priority_result}
        except Exception:
            pass

        # Weekly trends (last 7 days)
        weekly_result = db.execute(text("""
            SELECT
                date(created_at) as day,
                COUNT(*) as created,
                SUM(CASE WHEN status IN ('submitted', 'rejected') THEN 1 ELSE 0 END) as completed
            FROM human_input_requests
            WHERE created_at >= datetime('now', '-7 days')
            GROUP BY date(created_at)
            ORDER BY day
        """)).fetchall()
        weekly_trends = [{"day": str(row[0]), "created": row[1], "completed": row[2]} for row in weekly_result]

        # Fill in missing days with zeros
        all_days = {row[0] for row in weekly_result}
        for i in range(6, -1, -1):
            day_result = db.execute(text(f"SELECT date('now', '-{i} days')")).fetchone()
            if day_result:
                day_str = day_result[0]
                if day_str not in all_days:
                    weekly_trends.insert(0, {"day": day_str, "created": 0, "completed": 0})

        # Avg processing time
        avg_result = db.execute(text("""
            SELECT AVG(
                CASE
                    WHEN submitted_at IS NOT NULL AND created_at IS NOT NULL
                    THEN (julianday(submitted_at) - julianday(created_at)) * 24
                    ELSE NULL
                END
            )
            FROM human_input_requests
            WHERE submitted_at IS NOT NULL AND created_at IS NOT NULL
        """)).fetchone()
        avg_time = round(avg_result[0], 1) if avg_result and avg_result[0] else 0

        return {
            "total": total,
            "pending": pending,
            "submitted": submitted,
            "rejected": rejected,
            "avgProcessingTime": avg_time,
            "byType": by_type,
            "byPriority": by_priority,
            "weeklyTrends": weekly_trends,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计数据失败: {str(e)}")

@router.get("/review-stats", response_model=HumanReviewStats)
def get_human_review_stats(db: Session = Depends(get_db)):
    """
    获取人类审核统计信息

    GET /api/v1/human-input/review-stats
    返回: disputed/waiting_human/pending human_input 的数量，以及最近5条待处理项
    对应 goal-cb4c76143b4c 的需求
    """
    try:
        # 1. disputed tasks
        disputed_result = db.execute(text(
            "SELECT COUNT(*) FROM tasks WHERE status = 'disputed'"
        )).fetchone()
        disputed_count = disputed_result[0] if disputed_result else 0

        # 2. waiting_human tasks
        waiting_human_result = db.execute(text(
            "SELECT COUNT(*) FROM tasks WHERE status = 'waiting_human'"
        )).fetchone()
        waiting_human_count = waiting_human_result[0] if waiting_human_result else 0

        # 3. pending human_input_requests
        pending_result = db.execute(text(
            "SELECT COUNT(*) FROM human_input_requests WHERE status = 'pending'"
        )).fetchone()
        pending_count = pending_result[0] if pending_result else 0

        # 获取最近5条待处理项（按创建时间倒序）
        recent_items: List[Dict[str, Any]] = []

        # 从 tasks 表获取最近的 disputed 任务
        disputed_tasks = db.execute(text("""
            SELECT id, title, description, status, priority, created_at
            FROM tasks
            WHERE status = 'disputed'
            ORDER BY created_at DESC
            LIMIT 5
        """)).fetchall()

        for task in disputed_tasks:
            recent_items.append({
                "id": task.id,
                "type": "disputed",
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "created_at": str(task.created_at),
                "task_id": task.id
            })

        # 从 tasks 表获取最近的 waiting_human 任务
        waiting_tasks = db.execute(text("""
            SELECT id, title, description, status, priority, created_at
            FROM tasks
            WHERE status = 'waiting_human'
            ORDER BY created_at DESC
            LIMIT 5
        """)).fetchall()

        for task in waiting_tasks:
            recent_items.append({
                "id": task.id,
                "type": "waiting_human",
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "created_at": str(task.created_at),
                "task_id": task.id
            })

        # 从 human_input_requests 表获取最近的 pending 请求
        pending_requests = db.execute(text("""
            SELECT id, title, description, status, created_at, task_id
            FROM human_input_requests
            WHERE status = 'pending'
            ORDER BY created_at DESC
            LIMIT 5
        """)).fetchall()

        for req in pending_requests:
            recent_items.append({
                "id": req.id,
                "type": "pending_human_input",
                "title": req.title,
                "description": req.description,
                "status": req.status,
                "task_id": req.task_id,
                "created_at": str(req.created_at),
                "input_id": req.id
            })

        # 按创建时间排序，取最近的5条
        recent_items.sort(key=lambda x: x["created_at"], reverse=True)
        recent_items = recent_items[:5]

        return HumanReviewStats(
            disputed_count=disputed_count,
            waiting_human_count=waiting_human_count,
            pending_count=pending_count,
            recent_pending=recent_items
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取人类审核统计失败: {str(e)}")
