"""
Lifespan Handler — FastAPI 启动/关闭钩子

从 server.py 提取（2026-05-14）
"""
import asyncio
import json
from loguru import logger
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text

from api.app_state import get_reins, get_db_manager, set_probe_detector
from reins.nexus_log import LogEngine
from models import TriggerMode

@asynccontextmanager
async def lifespan_handler(app: FastAPI):
    # Phase 1: Init LogEngine
    try:
        LogEngine.init()
    except Exception:
        pass

    reins = get_reins()
    db_manager = get_db_manager()

    # ── 启动 ───────────────────────────────────────────────────────────────
    try:
        from reins.scheduler import NexusScheduler, set_scheduler
        sched = NexusScheduler(db_manager=db_manager)
        set_scheduler(sched)
        await sched.start()
        logger.info(f"[Startup] Scheduler started (tick={sched.stats.total_ticks})")
    except Exception as e:
        logger.error(f"[Startup] Scheduler start failed: {e}")

    try:
        from api.reports import init_report_repos
        init_report_repos(db_manager)
    except Exception as e:
        logger.warning(f"[Startup] Report repos init warning: {e}")

    try:
        with db_manager.engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, name, capability_tags, address, metadata, trigger_mode, "
                "poll_interval_seconds, model_name FROM agents WHERE health_status != 'removed'"
            )).fetchall()
        registered = 0
        for row in rows:
            try:
                ct = row.capability_tags or '{}'
                caps = json.loads(ct) if isinstance(ct, str) else (ct or {})
                # Extract technical capabilities from the new format for legacy register
                technical = caps.get("technical", []) if isinstance(caps, dict) else []
                reins.register_agent(
                    agent_id=row.id, name=row.name,
                    capabilities=technical,
                    address=row.address,
                    metadata=json.loads(row.metadata) if row.metadata else {},
                    trigger_mode=TriggerMode(row.trigger_mode or "sse"),
                    poll_interval_seconds=row.poll_interval_seconds or 10,
                    model_name=row.model_name or "",
                )
                registered += 1
            except Exception as e:
                logger.warning(f"[Startup] Failed to re-register agent {row.id}: {e}")
        logger.info(f"[Startup] Re-registered {registered} agents from DB")
    except Exception as e:
        logger.warning(f"[Startup] Agent re-registration warning: {e}")

    # ── 迁移 030：创建 system_config 表并预置配置 ──────────────────────────
    try:
        import importlib.util
        seed_path = os.path.join(
            os.path.dirname(__file__),
            "..", "persistence", "migrations", "030_seed_system_config.py"
        )
        spec = importlib.util.spec_from_file_location("seed_030", seed_path)
        seed_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(seed_mod)
        seed_mod.seed_system_config()
    except Exception as e:
        logger.warning(f"[Startup] Migration 030 seed warning: {e}")

    # ── 启动 Agent 主动健康探测器（Pull 模式）───────────────────────────
    try:
        from reins.api._agents_heartbeat_routes import AgentHealthProbeDetector
        reins = get_reins()
        probe_detector = AgentHealthProbeDetector(
            db_manager=db_manager,
            agent_registry=reins.agent_registry,
        )
        set_probe_detector(probe_detector)
        await probe_detector.start()
        logger.info("[Startup] Agent health probe detector started (Pull mode)")
    except Exception as e:
        logger.error(f"[Startup] Agent health probe start failed: {e}", exc_info=True)

    # 后台探测器由 events.py 在 Agent 注册时自动启动，无需手动调用
    logger.info("[Startup] ReinsServer fully ready")

    # ── 运行中 ─────────────────────────────────────────────────────────────
    yield

    # ── 关闭 ──────────────────────────────────────────────────────────────
    logger.info("[Shutdown] Shutting down...")
    try:
        from reins.scheduler import get_scheduler
        sched = get_scheduler()
        if sched:
            await sched.stop()
    except Exception as e:
        logger.warning(f"[Shutdown] Scheduler stop warning: {e}")

    try:
        # 停止 Agent 主动探测器
        from api.app_state import get_probe_detector
        detector = get_probe_detector()
        if detector:
            await detector.stop()
    except Exception as e:
        logger.warning(f"[Shutdown] Health probe stop warning: {e}")

    try:
        reins.stop()
    except Exception as e:
        logger.warning(f"[Shutdown] ReinsServer stop warning: {e}")

    try:
        db_manager.close()
    except Exception as e:
        logger.warning(f"[Shutdown] DB manager close warning: {e}")

    logger.info("[Shutdown] Done")
