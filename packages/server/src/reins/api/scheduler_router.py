"""
Scheduler + Health + Internal Router — 调度器统计/健康检查/内部任务管理
从 server.py 内联端点提取（2026-05-14）
"""
import json
from loguru import logger
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import text

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
        db = get_db_manager()
        with db.engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT id, title, assigned_agent, started_at, status FROM tasks
                WHERE status = 'in_progress' AND started_at IS NOT NULL AND started_at < :cutoff
                ORDER BY started_at ASC
            """), {"cutoff": cutoff}).fetchall()
        candidates = []
        for r in rows:
            candidates.append({
                "id": r.id, "title": r.title, "assigned_agent": r.assigned_agent,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "status": r.status,
                "minutes_overdue": int((datetime.now() - r.started_at).total_seconds() / 60) if r.started_at else None,
            })
        return {"timeout_minutes": timeout_minutes, "cutoff": cutoff.isoformat(),
                "candidate_count": len(candidates), "candidates": candidates}
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
        db = get_db_manager()
        with db.engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT id, name, health_status, status, last_heartbeat,
                       last_status_change, consecutive_offline_count,
                       current_tasks, load, max_concurrent_tasks
                FROM agents ORDER BY health_status, name
            """)).fetchall()
        agents = []
        for r in rows:
            agents.append({
                "id": r[0], "name": r[1], "health_status": r[2] or "unknown",
                "status": r[3], "last_heartbeat": str(r[4]) if r[4] else None,
                "last_status_change": str(r[5]) if r[5] else None,
                "consecutive_offline_count": r[6] or 0,
                "current_tasks": r[7] or 0, "load": r[8] or 0,
                "max_concurrent_tasks": r[9] or 5,
            })
        return agents
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
        where = "WHERE action = :action" if action else ""
        params = {"action": action} if action else {}
        with db.engine.connect() as conn:
            total = conn.execute(text(f"SELECT COUNT(*) FROM scheduler_log {where}"), params).fetchone()[0]
            rows = conn.execute(text(f"""
                SELECT id, tick_number, action, target_type, target_id,
                       detail, success, error, created_at FROM scheduler_log
                {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset
            """), {**params, "limit": page_size, "offset": offset}).fetchall()
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
