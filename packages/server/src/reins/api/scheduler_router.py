"""
Scheduler + Health + Internal Router — 调度器统计/健康检查/内部任务管理
从 server.py 内联端点提取（2026-05-14）
"""
import json
from loguru import logger
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy import Table, Column, String, Integer, DateTime, Boolean, Text, MetaData
from models import Task, Agent
from models.execution_log import ExecutionLog

# scheduler_log table has no ORM model, use SQLAlchemy Core
_metadata = MetaData()
_scheduler_log = Table('scheduler_log', _metadata,
    Column('id', Integer, primary_key=True),
    Column('tick_number', Integer),
    Column('action', String(100)),
    Column('target_type', String(50)),
    Column('target_id', String(100)),
    Column('detail', Text),
    Column('success', Boolean),
    Column('error', Text),
    Column('created_at', DateTime),
)

from api.app_state import get_db_manager
from reins.common.config import TASK_TIMEOUT_MINUTES

router = APIRouter(prefix="/api/v1", tags=["scheduler"])
internal_router = APIRouter(prefix="/internal", tags=["internal"])

@internal_router.post("/tasks/recover-timeout")
def recover_timeout_tasks(timeout_minutes: int = Query(TASK_TIMEOUT_MINUTES, ge=1, le=1440)):
    """回收超时任务（内部 API）"""
    from reins.core.background_tasks import TaskTimeoutDetector
    try:
        detector = TaskTimeoutDetector(db_manager=get_db_manager(), check_interval=300, timeout_minutes=timeout_minutes)
        result = detector.trigger_recovery(timeout_minutes=timeout_minutes)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recovery failed: {e}")

@internal_router.get("/tasks/timeout-candidates")
def list_timeout_candidates(timeout_minutes: int = Query(TASK_TIMEOUT_MINUTES, ge=1, le=1440)):
    """查看超时候选任务（预览）"""
    cutoff = datetime.now() - timedelta(minutes=timeout_minutes)
    try:
        session = get_db_manager().get_session()
        try:
            rows = session.query(Task).filter(
                Task.status == 'in_progress',
                Task.started_at.isnot(None),
                Task.started_at < int(cutoff.timestamp())
            ).order_by(Task.started_at.asc()).all()
            candidates = []
            for r in rows:
                candidates.append({
                    "id": r.id, "title": r.title, "assigned_agent": r.assigned_agent,
                    "started_at": r.started_at,
                    "status": r.status,
                    "minutes_overdue": int((datetime.now() - datetime.fromtimestamp(r.started_at)).total_seconds() / 60) if r.started_at else None,
                })
            return {"timeout_minutes": timeout_minutes, "cutoff": cutoff.isoformat(),
                    "candidate_count": len(candidates), "candidates": candidates}
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")

@router.get("/scheduler/stats")
def get_scheduler_stats():
    """获取调度器统计"""
    try:
        from reins.scheduler import get_scheduler
        sched = get_scheduler()
        if not sched:
            raise HTTPException(status_code=503, detail="Scheduler not started")
        return sched.stats.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler stats: {e}")

@router.get("/scheduler/agents/health")
def get_agent_health():
    """获取 Agent 健康度列表"""
    try:
        session = get_db_manager().get_session()
        try:
            rows = session.query(Agent).order_by(Agent.health_status, Agent.name).all()
            agents = []
            for r in rows:
                agents.append({
                    "id": r.id, "name": r.name, "health_status": r.health_status or "unknown",
                    "status": r.status, "last_heartbeat": str(r.last_heartbeat) if r.last_heartbeat else None,
                    "last_status_change": str(r.last_status_change) if r.last_status_change else None,
                    "consecutive_offline_count": r.consecutive_offline_count or 0,
                    "current_tasks": r.current_tasks or 0, "load": r.load or 0,
                    "max_concurrent_tasks": r.max_concurrent_tasks or 5,
                })
            return agents
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent health: {e}")

@router.get("/scheduler/logs")
def get_scheduler_logs(
    action: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取调度日志"""
    try:
        db = get_db_manager()
        offset = (page - 1) * page_size
        with db.engine.connect() as conn:
            count_query = func.count().select().select_from(_scheduler_log)
            query = _scheduler_log.select().order_by(_scheduler_log.c.created_at.desc()).limit(page_size).offset(offset)
            if action:
                count_query = count_query.where(_scheduler_log.c.action == action)
                query = query.where(_scheduler_log.c.action == action)
            total = conn.execute(count_query).scalar()
            rows = conn.execute(query).fetchall()
        items = []
        for r in rows:
            items.append({
                "id": r[0], "tick_number": r[1], "action": r[2],
                "target_type": r[3], "target_id": r[4], "detail": r[5],
                "success": r[6], "error": r[7],
                "created_at": r[8].isoformat() if hasattr(r[8], 'isoformat') else str(r[8]),
            })
        return {"items": items, "total": total, "page": page, "page_size": page_size}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler logs: {e}")

@router.post("/scheduler/tick")
def trigger_scheduler_tick():
    """手动触发一次调度周期（调试/运维用）。

    会执行：
    1. 任务分配扫描
    2. 超时任务回收
    3. 依赖解锁扫描
    4. Agent 负载平衡
    """
    try:
        from reins.scheduler import get_scheduler
        import asyncio

        sched = get_scheduler()
        if not sched:
            raise HTTPException(status_code=503, detail="Scheduler not started")

        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.create_task(sched._tick())
                tick_number = sched.stats.total_ticks
                return {
                    "status": "scheduled",
                    "message": "Tick scheduled in running event loop",
                    "current_tick": tick_number,
                }
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(sched._tick())
                tick_number = sched.stats.total_ticks
                return {
                    "status": "completed",
                    "message": "Tick executed synchronously",
                    "current_tick": tick_number,
                }
            finally:
                loop.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger scheduler tick: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger tick: {e}")

@router.post("/scheduler/dependencies/unlock")
def trigger_dependency_unlock():
    """手动触发依赖解锁扫描"""
    try:
        from reins.scheduler import get_scheduler
        sched = get_scheduler()
        if not sched:
            raise HTTPException(status_code=503, detail="Scheduler not started")
        unlocked = sched.dependency_resolver.scan_blocked()
        return {"unlocked_count": len(unlocked), "task_ids": unlocked}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unlock dependencies: {e}")

@router.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "reins"}
