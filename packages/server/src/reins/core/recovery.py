# -*- coding: utf-8 -*-
"""
Nexus 故障恢复脚本 (reins/recovery.py)
清理卡住的任务 + 回收离线 Worker 的任务
"""
import asyncio
from loguru import logger
from datetime import datetime, timedelta
from sqlalchemy import text

# 超时阈值
VERIFICATION_TIMEOUT_HOURS = 1   # verifying 超过 1 小时 -> 重置
BLOCK_TIMEOUT_HOURS = 24          # blocked/timeout 超过 24 小时 -> 重置
OFFLINE_THRESHOLD_MINUTES = 90   # 心跳超过 90 分钟 -> 标记 offline + 回收任务

def cleanup_zombie_tasks(db_session):
    """
    清理僵尸任务:
    - verifying 超过 VERIFICATION_TIMEOUT_HOURS -> 重置为 todo
    - blocked/timeout 超过 BLOCK_TIMEOUT_HOURS -> 重置为 todo
    """
    now = datetime.now()
    cleaned = []

    # 清理 verifying 僵尸
    verifying_deadline = now - timedelta(hours=VERIFICATION_TIMEOUT_HOURS)
    result = db_session.execute(text("""
        SELECT id, title, assigned_agent, status, updated_at
        FROM tasks
        WHERE status = 'verifying'
        AND updated_at < :deadline
    """), {'deadline': verifying_deadline.isoformat()})
    zombie_v = result.fetchall()
    if zombie_v:
        ids = [r[0] for r in zombie_v]
        placeholders = ', '.join([f':id{i}' for i in range(len(ids))])
        params = {f'id{i}': id for i, id in enumerate(ids)}
        params['now'] = now.isoformat()
        db_session.execute(text(f"""
            UPDATE tasks
            SET status = 'todo', assigned_agent = NULL, updated_at = :now
            WHERE id IN ({placeholders})
        """), params)
        cleaned.append(f'verifying: {len(zombie_v)} tasks -> todo')
        for r in zombie_v:
            logger.info(f"  [CLEAN] verifying: {r[0]} agent={r[2]} updated={r[4]}")

    # 清理 blocked/timeout 僵尸
    block_deadline = now - timedelta(hours=BLOCK_TIMEOUT_HOURS)
    result = db_session.execute(text("""
        SELECT id, title, status, updated_at
        FROM tasks
        WHERE status IN ('blocked', 'timeout')
        AND updated_at < :deadline
    """), {'deadline': block_deadline.isoformat()})
    zombie_b = result.fetchall()
    if zombie_b:
        ids = [r[0] for r in zombie_b]
        placeholders = ', '.join([f':id{i}' for i in range(len(ids))])
        params = {f'id{i}': id for i, id in enumerate(ids)}
        params['now'] = now.isoformat()
        db_session.execute(text(f"""
            UPDATE tasks
            SET status = 'todo', assigned_agent = NULL, updated_at = :now
            WHERE id IN ({placeholders})
        """), params)
        cleaned.append(f'blocked/timeout: {len(zombie_b)} tasks -> todo')
        for r in zombie_b:
            logger.info(f"  [CLEAN] {r[2]}: {r[0]} updated={r[3]}")

    db_session.commit()
    return cleaned

def recover_offline_agents(db_session, offline_threshold_minutes=OFFLINE_THRESHOLD_MINUTES):
    """
    回收离线 Worker 的任务:
    - 心跳超过 offline_threshold_minutes 的 agent -> 标记为 offline
    - 其 in_progress/verifying 任务 -> 重置为 todo
    """
    deadline = datetime.now() - timedelta(minutes=offline_threshold_minutes)
    recovered = []

    # 找离线超时的 agent
    result = db_session.execute(text("""
        SELECT id, name, status, last_heartbeat
        FROM agents
        WHERE last_heartbeat < :deadline
        AND status != 'offline'
    """), {'deadline': deadline.isoformat()})
    offline_agents = result.fetchall()

    if not offline_agents:
        logger.info("  [RECOVER] no offline agents found")
        return recovered

    now = datetime.now()
    for agent in offline_agents:
        agent_id, agent_name, old_status, last_hb = agent
        logger.info(f"  [RECOVER] agent={agent_name} (id={agent_id}) last_hb={last_hb} status={old_status}")

        # 回收该 agent 的卡住任务
        result2 = db_session.execute(text("""
            SELECT id, title, status
            FROM tasks
            WHERE assigned_agent = :agent_id
            AND status IN ('in_progress', 'verifying')
        """), {'agent_id': agent_id})
        stuck_tasks = result2.fetchall()

        if stuck_tasks:
            task_ids = [t[0] for t in stuck_tasks]
            placeholders = ', '.join([f':tid{i}' for i in range(len(task_ids))])
            params = {f'tid{i}': tid for i, tid in enumerate(task_ids)}
            params['now'] = now.isoformat()
            db_session.execute(text(f"""
                UPDATE tasks
                SET status = 'todo', assigned_agent = NULL, updated_at = :now
                WHERE id IN ({placeholders})
            """), params)
            recovered.append(f'{agent_name}: {len(stuck_tasks)} tasks')
            for t in stuck_tasks:
                logger.info(f"    [RECOVER] task={t[0]} status={t[2]}")

        # 标记 agent 为 offline
        db_session.execute(text("""
            UPDATE agents
            SET status = 'offline', updated_at = :now
            WHERE id = :agent_id
        """), {'agent_id': agent_id, 'now': now.isoformat()})
        logger.info(f"  [RECOVER] marked {agent_name} as offline")

    db_session.commit()
    return recovered

def start_periodic_recovery(interval_seconds: int = 300):
    """
    启动周期性心跳超时自动回收任务。
    在后台 asyncio task 中每 interval_seconds 秒执行一次
    cleanup_zombie_tasks() + recover_offline_agents()。
    """
    async def _periodic_loop():
        while True:
            try:
                from reins.common.database import get_db_session
                db = get_db_session()
                try:
                    cleaned = cleanup_zombie_tasks(db)
                    for msg in cleaned:
                        logger.info(f"[PeriodicRecovery] Cleanup: {msg}")
                    recovered = recover_offline_agents(db)
                    for msg in recovered:
                        logger.info(f"[PeriodicRecovery] Recover: {msg}")
                    if not cleaned and not recovered:
                        logger.debug("[PeriodicRecovery] No zombie tasks or offline agents found")
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"[PeriodicRecovery] Error during periodic recovery: {e}")
            await asyncio.sleep(interval_seconds)

    asyncio.create_task(_periodic_loop(), name="periodic-recovery")
    logger.info(f"[PeriodicRecovery] Started with interval={interval_seconds}s")

if __name__ == '__main__':
    import sys
    from pathlib import Path

    # reins/recovery.py 位于 src/reins/，parent.parent = src/
    src_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(src_root))
    sys.stdout.reconfigure(encoding='utf-8')

    from reins.common.database import get_db_session

    logger.info('=' * 60)
    logger.info('Sprint 61.1: Zombie Task Cleanup + Offline Worker Recovery')
    logger.info(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    logger.info('=' * 60)

    db = get_db_session()
    try:
        logger.info('\n[1] Cleanup zombie tasks...')
        cleaned = cleanup_zombie_tasks(db)
        if cleaned:
            for msg in cleaned:
                logger.info(f'  Done: {msg}')
        else:
            logger.info('  No zombie tasks found')

        logger.info('\n[2] Recover offline agents...')
        recovered = recover_offline_agents(db)
        if recovered:
            for msg in recovered:
                logger.info(f'  Done: {msg}')
        else:
            logger.info('  No offline agents found')

        logger.info('\n[3] Verify final state...')
        result = db.execute(text("SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"))
        logger.info('  Task status:')
        for row in result:
            logger.info(f'    {row[0]:20s}: {row[1]}')

        result = db.execute(text("SELECT id, name, status, last_heartbeat FROM agents ORDER BY name"))
        logger.info('  Agent status:')
        for row in result:
            logger.info(f'    {row[0]:10s} name={row[1]:10s} status={row[2]:10s} last_hb={row[3]}')

        logger.info('\n[Sprint 61.1] Cleanup completed successfully')
    finally:
        db.close()
