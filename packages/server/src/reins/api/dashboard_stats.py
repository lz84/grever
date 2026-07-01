"""
Dashboard Stats API

Sprint 26: Dashboard 指标卡 + 实时数据刷新
提供统一的统计数据端点，避免前端聚合计算
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import date, datetime, timedelta
from models import Task, Agent, Scenario, Goal

from reins.common.database import get_db

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    获取 Dashboard 统计数据

    Returns:
        active_tasks: 活跃任务数 (in_progress 或 running)
        completed_today: 今日完成任务数
        online_agents: 在线 Agent 数 (status = running)
        total_scenarios: 场景库总数
        total_goals: 目标总数
        active_goals: 进行中目标数
    """
    try:
        today = date.today().isoformat()

        active_tasks = db.query(func.count(Task.id)).filter(
            Task.status.in_(['in_progress', 'running'])
        ).scalar() or 0

        completed_today = db.query(func.count(Task.id)).filter(
            Task.status.in_(['done', 'completed']),
            Task.completed_at.isnot(None),
            func.date(Task.completed_at) == today
        ).scalar() or 0

        online_agents = db.query(func.count(Agent.id)).filter(
            Agent.status == 'online'
        ).scalar() or 0

        total_scenarios = db.query(func.count(Scenario.id)).scalar() or 0
        total_goals = db.query(func.count(Goal.id)).scalar() or 0
        active_goals = db.query(func.count(Goal.id)).filter(
            Goal.status.in_(['in_progress', 'active'])
        ).scalar() or 0

        return {
            "active_tasks": active_tasks,
            "completed_today": completed_today,
            "online_agents": online_agents,
            "total_scenarios": total_scenarios,
            "total_goals": total_goals,
            "active_goals": active_goals,
        }
    except Exception as e:
        return {
            "active_tasks": 0,
            "completed_today": 0,
            "online_agents": 0,
            "total_scenarios": 0,
            "total_goals": 0,
            "active_goals": 0,
            "error": str(e)
        }

@router.get("/stats/execution-trend")
def get_execution_trend(days: int = Query(7, ge=1, le=30), db: Session = Depends(get_db)):
    """
    获取近 N 天任务完成趋势数据

    Returns:
        List of {date, count} for each of the past N days
    """
    try:
        today = date.today()
        trend = []
        for i in range(days - 1, -1, -1):
            day = today - timedelta(days=i)
            day_str = day.isoformat()
            count = db.query(func.count(Task.id)).filter(
                Task.status.in_(['done', 'completed']),
                Task.completed_at.isnot(None),
                func.date(Task.completed_at) == day_str
            ).scalar() or 0
            trend.append({"date": day_str, "count": count})
        return trend
    except Exception as e:
        return []
