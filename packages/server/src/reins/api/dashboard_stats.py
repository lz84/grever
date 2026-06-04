"""
Dashboard Stats API

Sprint 26: Dashboard 指标卡 + 实时数据刷新
提供统一的统计数据端点，避免前端聚合计算
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date

from reins.common.database import get_db

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    获取 Dashboard 统计数据（优化：使用 COUNT 查询替代全表扫描）

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

        # 使用 COUNT 聚合查询，避免全表拉取
        active_tasks = db.execute(text(
            "SELECT COUNT(*) FROM tasks WHERE status IN ('in_progress', 'running')"
        )).scalar() or 0

        completed_today = db.execute(text(
            "SELECT COUNT(*) FROM tasks WHERE status IN ('done', 'completed') AND completed_at IS NOT NULL AND DATE(completed_at) = :today"
        ), {"today": today}).scalar() or 0

        online_agents = db.execute(text(
            "SELECT COUNT(*) FROM agents WHERE status = 'running'"
        )).scalar() or 0

        total_scenarios = db.execute(text(
            "SELECT COUNT(*) FROM scenarios"
        )).scalar() or 0

        total_goals = db.execute(text(
            "SELECT COUNT(*) FROM goals"
        )).scalar() or 0

        active_goals = db.execute(text(
            "SELECT COUNT(*) FROM goals WHERE status IN ('in_progress', 'active')"
        )).scalar() or 0

        return {
            "active_tasks": active_tasks,
            "completed_today": completed_today,
            "online_agents": online_agents,
            "total_scenarios": total_scenarios,
            "total_goals": total_goals,
            "active_goals": active_goals,
        }
    except Exception as e:
        # 如果表不存在，返回默认值
        return {
            "active_tasks": 0,
            "completed_today": 0,
            "online_agents": 0,
            "total_scenarios": 0,
            "total_goals": 0,
            "active_goals": 0,
            "error": str(e)
        }
