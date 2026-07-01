"""人类输入 API - 统计端点"""
from loguru import logger
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Task, HumanInputRequest

from reins.common.database import get_db
from reins.api.human_input_models import HumanReviewStats

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

        # Total counts - converted to ORM
        total = db.query(func.count(HumanInputRequest.id)).scalar() or 0
        pending = db.query(func.count(HumanInputRequest.id)).filter(
            HumanInputRequest.status == 'pending'
        ).scalar() or 0
        submitted = db.query(func.count(HumanInputRequest.id)).filter(
            HumanInputRequest.status == 'submitted'
        ).scalar() or 0
        rejected = db.query(func.count(HumanInputRequest.id)).filter(
            HumanInputRequest.status == 'rejected'
        ).scalar() or 0

        # By type
        by_type_rows = db.query(HumanInputRequest.input_type, func.count(HumanInputRequest.id)).group_by(
            HumanInputRequest.input_type
        ).all()
        by_type = {row[0]: row[1] for row in by_type_rows}

        # By priority (if priority field exists)
        by_priority = {}
        try:
            priority_rows = db.query(
                func.coalesce(HumanInputRequest.priority, 'none'),
                func.count(HumanInputRequest.id)
            ).group_by(func.coalesce(HumanInputRequest.priority, 'none')).all()
            by_priority = {row[0]: row[1] for row in priority_rows}
        except Exception:
            pass

        # Weekly trends - converted to ORM
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=7)
        from sqlalchemy import case
        weekly_result = db.query(
            HumanInputRequest.created_at,
            func.count(HumanInputRequest.id)
        ).filter(
            HumanInputRequest.created_at >= cutoff
        ).group_by(
            func.date(HumanInputRequest.created_at)
        ).order_by(
            func.date(HumanInputRequest.created_at)
        ).all()
        weekly_trends = [{"day": str(row[0].date()) if row[0] else "", "created": row[1], "completed": 0} for row in weekly_result]

        # Count completed per day via ORM
        completed_result = db.query(
            func.date(HumanInputRequest.created_at),
            func.count(HumanInputRequest.id)
        ).filter(
            HumanInputRequest.created_at >= cutoff,
            HumanInputRequest.status.in_(['submitted', 'rejected'])
        ).group_by(
            func.date(HumanInputRequest.created_at)
        ).all()
        completed_map = {str(row[0]): row[1] for row in completed_result}
        for t in weekly_trends:
            t["completed"] = completed_map.get(t["day"], 0)

        # Fill in missing days with zeros
        all_days = {t["day"] for t in weekly_trends}
        for i in range(6, -1, -1):
            day_str = (datetime.utcnow() - timedelta(days=i)).date().isoformat()
            if day_str not in all_days:
                weekly_trends.append({"day": day_str, "created": 0, "completed": 0})
        weekly_trends.sort(key=lambda x: x["day"])

        # Avg processing time - converted to ORM
        avg_result = db.query(
            func.avg(
                func.julianday(HumanInputRequest.submitted_at) - func.julianday(HumanInputRequest.created_at)
            ) * 24
        ).filter(
            HumanInputRequest.submitted_at.isnot(None),
            HumanInputRequest.created_at.isnot(None)
        ).scalar()
        avg_time = round(float(avg_result), 1) if avg_result else 0

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
    """
    try:
        # COUNT queries converted to ORM
        disputed_count = db.query(func.count(Task.id)).filter(Task.status == 'disputed').scalar() or 0
        waiting_human_count = db.query(func.count(Task.id)).filter(Task.status == 'waiting_human').scalar() or 0
        pending_count = db.query(func.count(HumanInputRequest.id)).filter(
            HumanInputRequest.status == 'pending'
        ).scalar() or 0

        recent_items: List[Dict[str, Any]] = []

        # Recent disputed tasks - converted to ORM
        disputed_tasks = db.query(Task).filter(Task.status == 'disputed').order_by(
            Task.created_at.desc()
        ).limit(5).all()
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

        # Recent waiting_human tasks - converted to ORM
        waiting_tasks = db.query(Task).filter(Task.status == 'waiting_human').order_by(
            Task.created_at.desc()
        ).limit(5).all()
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

        # Recent pending human_input_requests - converted to ORM
        pending_requests = db.query(HumanInputRequest).filter(
            HumanInputRequest.status == 'pending'
        ).order_by(HumanInputRequest.created_at.desc()).limit(5).all()
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
