"""Agent heartbeat 路由子模块"""
import json
import os
import time
from loguru import logger
import uuid as _uuid_lib
import datetime
from datetime import datetime as _dt
from typing import Optional

from fastapi import APIRouter
from sqlalchemy import text

from api.app_state import get_reins, get_db_manager
from reins.api._agents_register_routes import HeartbeatRequest

router = APIRouter()

@router.post("/agents/{agent_id}/heartbeat")
def heartbeat_agent(agent_id: str, body: Optional[HeartbeatRequest] = None):
    """Agent 心跳（增强版 - 返回 pending 任务）"""
    reins = get_reins()
    db = get_db_manager()
    status_dict = None
    if body:
        # 兼容两种前端格式：
        # 旧格式：status="online"（字符串）
        # 新格式：status={state: "working", load: 30, current_tasks: 0}（对象）
        raw_status = body.status
        if isinstance(raw_status, dict):
            status_dict = {k: v for k, v in raw_status.items() if v is not None}
        else:
            status_dict = {k: v for k, v in {
                "status": raw_status, "state": body.state,
                "load": body.load, "current_tasks": body.current_tasks,
                "latency_ms": body.latency_ms,
            }.items() if v is not None}

    success = reins.heartbeat_agent(agent_id, status_dict)
    hb_start = time.time()

    # 查询实时 agent 数据
    _db_load = _db_ct = _db_model = _db_caps = None
    try:
        with db.engine.connect() as conn:
            row = conn.execute(text(
                "SELECT load, current_tasks, model_name, capability_tags FROM agents WHERE id = :aid"
            ), {"aid": agent_id}).fetchone()
            if row:
                _db_load, _db_ct, _db_model = row.load, row.current_tasks, row.model_name
                if row.capability_tags:
                    try:
                        _db_caps = json.loads(row.capability_tags)
                    except Exception:
                        pass
    except Exception:
        pass

    # 写 heartbeat_logs + 更新 agents
    try:
        from persistence.tables import heartbeat_logs
        from reins.scheduler.heartbeat_decision import HeartbeatDecision
        decision = HeartbeatDecision(db).on_heartbeat_success(agent_id)
        decided = decision.get("new_state", "online")
        
        # 构建 UPDATE 语句（动态添加 model_name / capability_tags）
        update_fields = {
            "now": _dt.now(), "ds": decided,
            "cc": decision.get("failure_count_reset", 0),
            "load": _db_load, "ct": _db_ct, "aid": agent_id
        }
        update_sql_parts = [
            "last_heartbeat=:now", "health_status=:ds", "status=:ds",
            "consecutive_offline_count=:cc",
            "load=CASE WHEN :load IS NOT NULL AND :load>0 THEN :load ELSE load END",
            "current_tasks=CASE WHEN :ct IS NOT NULL THEN :ct ELSE current_tasks END",
            "updated_at=:now"
        ]
        
        # 如果心跳携带了 model_name，更新它
        if body and body.model_name:
            update_sql_parts.append("model_name=:model_name")
            update_fields["model_name"] = body.model_name
            logger.info(f"[Heartbeat] Agent {agent_id} reporting model: {body.model_name}")
        
        # 如果心跳携带了 capability_tags，更新它
        if body and body.capability_tags:
            update_sql_parts.append("capability_tags=:caps")
            update_fields["caps"] = json.dumps(body.capability_tags)
            logger.info(f"[Heartbeat] Agent {agent_id} reporting caps: {list(body.capability_tags.keys())}")
        
        update_sql = "UPDATE agents SET " + ", ".join(update_sql_parts) + " WHERE id=:aid"
        
        raw_payload = json.dumps(body.model_dump(exclude_none=True)) if body else None

        with db.engine.begin() as conn:
            conn.execute(heartbeat_logs.insert().values(
                id=str(_uuid_lib.uuid4()), agent_id=agent_id, timestamp=_dt.now(),
                status=decided, latency_ms=body.latency_ms if body else None,
                load=_db_load, current_tasks=_db_ct, raw_payload=raw_payload))
            conn.execute(text(update_sql), update_fields)
    except Exception as e:
        logger.warning(f"[P5-05] heartbeat log warning: {e}")

    # 查 pending 任务（改用统一上下文构建器）
    result = {"success": success}
    try:
        from reins.scheduler.task_context_builder import build_task_execution_context
        with db.engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT t.id, t.title, t.description, p.goal_id, t.priority,
                       t.project_id,
                       g.title as gt, g.description as gd,
                       p.name as pname, p.description as pdesc
                FROM tasks t LEFT JOIN projects p ON t.project_id=p.id
                LEFT JOIN goals g ON p.goal_id=g.id
                WHERE t.assigned_agent=:aid AND t.status IN ('todo','pending','review_needed','waiting')
                  -- Project 级别依赖链检查：父 Project 的所有依赖 Project 必须全部完成
                  AND NOT EXISTS (
                      SELECT 1 
                      FROM projects parent_proj
                      JOIN projects dep_proj ON dep_proj.id = parent_proj.depends_on
                      WHERE parent_proj.id = t.project_id
                        AND dep_proj.status != 'done'
                  )
                ORDER BY CASE t.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                         WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END, t.created_at ASC
                LIMIT 10
            """), {"aid": agent_id}).fetchall()

            assigned = []
            for r in rows:
                # 用统一构建器拿到完整的三级上下文 + 附件 + 统一 prompt
                base_url = os.environ.get("NEXUS_BASE_URL", "http://127.0.0.1:8097")
                full_ctx = build_task_execution_context(r.id, db, include_attachments=True, base_url=base_url)

                assigned.append({
                    "id": r.id,
                    "title": r.title,
                    "description": r.description,
                    "goal_id": r.goal_id,
                    "priority": r.priority,
                    "context": {
                        "goal_info": {
                            "id": full_ctx["goal"].get("id"),
                            "title": full_ctx["goal"].get("title"),
                            "description": full_ctx["goal"].get("description"),
                        },
                        "project_info": {
                            "id": full_ctx["project"].get("id"),
                            "name": full_ctx["project"].get("name"),
                            "description": full_ctx["project"].get("description"),
                        },
                        "task_info": {
                            "id": full_ctx["task"].get("id"),
                            "title": full_ctx["task"].get("title"),
                            "description": full_ctx["task"].get("description"),
                            "acceptance_criteria": full_ctx["task"].get("acceptance_criteria"),
                            "dependencies": full_ctx["dependencies"],
                        },
                        "attachments": full_ctx["attachments"],
                        "prompt": full_ctx["prompt"],
                    },
                })
            result["assigned_tasks"] = assigned
    except Exception as e:
        logger.warning(f"[MAK-214] heartbeat tasks warning: {e}")

    # 补充 agent 实时信息
    try:
        with db.engine.connect() as conn:
            row = conn.execute(text(
                "SELECT load, current_tasks, model_name, capability_tags FROM agents WHERE id = :aid"
            ), {"aid": agent_id}).fetchone()
            if row:
                result["agent_load"] = row.load
                result["current_tasks"] = row.current_tasks
                result["model_name"] = row.model_name
                if row.capability_tags:
                    try:
                        result["capability_tags"] = json.loads(row.capability_tags)
                    except Exception:
                        pass
    except Exception:
        pass

    # 写 execution_logs
    try:
        from persistence.tables import execution_logs
        with db.engine.begin() as conn:
            conn.execute(execution_logs.insert().values(
                id=str(_uuid_lib.uuid4()), task_id=None, agent_id=agent_id,
                action='heartbeat',
                input=json.dumps({"status": body.status if body else None}),
                output=json.dumps({"assigned_tasks": len(result.get("assigned_tasks", [])), "success": success}),
                status='success' if success else 'failure',
                duration_ms=int((time.time() - hb_start) * 1000),
                created_at=_dt.now(),
                error_message='' if success else 'heartbeat failed',
                result_summary=f"heartbeat success, returned {len(result.get('assigned_tasks', []))} tasks",
                metadata=json.dumps({"source": "heartbeat_endpoint"}),
                connectivity_verified=success,
            ))
    except Exception:
        pass

    return result


# === Agent Health Probe (merged from agent_health_probe.py) ===

import asyncio
from loguru import logger
import time
import httpx
from datetime import datetime
from typing import Optional

from reins.scheduler.load_calculator import update_agent_load

# 默认值（会被 system_config 覆盖）
DEFAULT_PROBE_INTERVAL = 300      # 5 分钟
DEFAULT_PROBE_TIMEOUT = 5         # 5 秒
DEFAULT_PROBE_PATH = "/health"
DEFAULT_PROBE_ENABLED = True

class AgentHealthProbeDetector:
    """
    Agent 主动健康探测器（Pull 模式）

    后台定时任务：
    - 从 system_config 读取探测参数（interval / timeout / path / enabled）
    - 遍历所有已注册 Agent
    - 向每个 Agent 的 address + probe_path 发 GET 请求
    - 根据响应更新 Agent 的 last_heartbeat 和 status
    """

    def __init__(
        self,
        db_manager,
        agent_registry,
        check_interval: float | None = None,
    ):
        self._db_manager = db_manager
        self._agent_registry = agent_registry
        self._check_interval = check_interval  # None = 从 system_config 读取
        self._task: asyncio.Task | None = None
        self._running = False

    # ── 配置读取 ──────────────────────────────────────────────────────

    def _get_config(self, key: str, default):
        """从 system_config 表读取配置值"""
        try:
            from sqlalchemy import text
            with self._db_manager.engine.connect() as conn:
                row = conn.execute(
                    text("SELECT value FROM system_config WHERE category='agent' AND key=:key"),
                    {"key": key},
                ).fetchone()
            if row and row[0]:
                raw = row[0].strip('"')
                if raw.lower() == "true":
                    return True
                if raw.lower() == "false":
                    return False
                try:
                    return int(raw)
                except ValueError:
                    try:
                        return float(raw)
                    except ValueError:
                        return raw
            return default
        except Exception:
            return default

    # ── 生命周期 ──────────────────────────────────────────────────────

    async def start(self):
        """启动后台探测"""
        if self._running:
            return
        self._running = True

        # 首次读取配置
        enabled = self._get_config("agent_probe_enabled", DEFAULT_PROBE_ENABLED)
        if not enabled:
            logger.info("[AgentHealthProbe] Disabled by config, not starting")
            return

        interval = self._get_config(
            "agent_probe_interval_seconds", DEFAULT_PROBE_INTERVAL
        )
        timeout = self._get_config(
            "agent_probe_timeout_seconds", DEFAULT_PROBE_TIMEOUT
        )
        probe_path = self._get_config(
            "agent_probe_path", DEFAULT_PROBE_PATH
        )

        logger.info(
            f"[AgentHealthProbe] Started (interval={interval}s, timeout={timeout}s, path={probe_path})"
        )
        self._task = asyncio.create_task(self._run(interval, timeout, probe_path))

    async def stop(self):
        """停止后台探测"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[AgentHealthProbe] Stopped")

    # ── 探测循环 ──────────────────────────────────────────────────────

    async def _run(self, interval: float, timeout: float, probe_path: str):
        """探测主循环"""
        while self._running:
            try:
                # 每次循环重新读取配置（支持热更新）
                enabled = self._get_config("agent_probe_enabled", DEFAULT_PROBE_ENABLED)
                if not enabled:
                    logger.info("[AgentHealthProbe] Disabled by config, waiting...")
                else:
                    current_timeout = self._get_config(
                        "agent_probe_timeout_seconds", timeout
                    )
                    current_path = self._get_config("agent_probe_path", probe_path)
                    await self._probe_all_agents(current_timeout, current_path)
            except Exception as e:
                logger.error(f"[AgentHealthProbe] Probe error: {e}")

            await asyncio.sleep(interval)

    # ── 探测逻辑 ──────────────────────────────────────────────────────

    async def _probe_all_agents(self, timeout: float, probe_path: str):
        """探测所有已注册 Agent"""
        from sqlalchemy import text

        with self._db_manager.engine.connect() as conn:
            agents = conn.execute(
                text("""
                    SELECT id, name, address, status, last_heartbeat
                    FROM agents
                    WHERE health_status != 'removed'
                    ORDER BY id
                """)
            ).fetchall()

        if not agents:
            logger.debug("[AgentHealthProbe] No agents to probe")
            return

        results = {"total": len(agents), "online": 0, "offline": 0, "errors": 0}

        for agent in agents:
            result = await self._probe_single(agent.id, agent.name, agent.address, timeout, probe_path)
            if result == "online":
                results["online"] += 1
            elif result == "offline":
                results["offline"] += 1
            else:
                results["errors"] += 1

        logger.info(
            f"[AgentHealthProbe] Probe complete: {results['online']} online, "
            f"{results['offline']} offline, {results['errors']} errors"
        )

    async def _probe_single(
        self, agent_id: str, name: str, address: Optional[str],
        timeout: float, probe_path: str
    ) -> str:
        """探测单个 Agent，返回 'online' / 'offline' / 'error'"""
        from sqlalchemy import text

        if not address:
            logger.debug(f"[AgentHealthProbe] {name} ({agent_id}): no address, skipping")
            return "error"

        base_url = address.rstrip("/")
        url = f"{base_url}{probe_path}"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url)
                status_code = resp.status_code
        except httpx.ConnectError:
            status_code = 0
        except Exception as e:
            logger.debug(f"[AgentHealthProbe] {name} ({agent_id}): probe exception: {e}")
            status_code = -1

        now = datetime.now()

        if status_code > 0 and status_code < 500:
            # 在线：更新 last_heartbeat + status
            with self._db_manager.engine.begin() as conn:
                conn.execute(
                    text("""
                        UPDATE agents
                        SET last_heartbeat = :now,
                            status = 'online',
                            health_status = 'online',
                            consecutive_offline_count = 0,
                            updated_at = :now
                        WHERE id = :aid
                    """),
                    {"now": now, "aid": agent_id},
                )
            logger.debug(
                f"[AgentHealthProbe] ✅ {name} ({agent_id}): online "
                f"(HTTP {status_code} at {url})"
            )
            return "online"
        else:
            # 离线：增加 offline count，超过阈值标记 offline
            with self._db_manager.engine.connect() as conn:
                row = conn.execute(
                    text("""
                        SELECT consecutive_offline_count, max_offline_before_deactivate, status
                        FROM agents WHERE id = :aid
                    """),
                    {"aid": agent_id},
                ).fetchone()

            if row:
                current_count = row[0] or 0
                max_offline = row[2] or 3
                current_status = row[2] or "online"

                new_count = current_count + 1
                if new_count >= max_offline:
                    new_status = "offline"
                    new_count = 0  # 重置
                else:
                    new_status = current_status

                with self._db_manager.engine.begin() as conn:
                    conn.execute(
                        text("""
                            UPDATE agents
                            SET consecutive_offline_count = :count,
                                status = :status,
                                health_status = :status,
                                updated_at = :now
                            WHERE id = :aid
                        """),
                        {"count": new_count, "status": new_status, "now": now, "aid": agent_id},
                    )

            logger.debug(
                f"[AgentHealthProbe] ❌ {name} ({agent_id}): offline "
                f"(HTTP {status_code} at {url}, fail_count={current_count + 1})"
            )
            return "offline"


"""
Agent 主动健康探测器（Pull 模式）

定时向每个 Agent 的 address + probe_path 发 HTTP 请求，探测活性。
探测间隔 / 超时 / 路径均可通过 system_config 配置。
"""

import asyncio
from loguru import logger
import time
import httpx
from datetime import datetime
from typing import Optional

from reins.scheduler.load_calculator import update_agent_load

# 默认值（会被 system_config 覆盖）
DEFAULT_PROBE_INTERVAL = 300      # 5 分钟
DEFAULT_PROBE_TIMEOUT = 5         # 5 秒
DEFAULT_PROBE_PATH = "/health"
DEFAULT_PROBE_ENABLED = True

class AgentHealthProbeDetector:
    """
    Agent 主动健康探测器（Pull 模式）

    后台定时任务：
    - 从 system_config 读取探测参数（interval / timeout / path / enabled）
    - 遍历所有已注册 Agent
    - 向每个 Agent 的 address + probe_path 发 GET 请求
    - 根据响应更新 Agent 的 last_heartbeat 和 status
    """

    def __init__(
        self,
        db_manager,
        agent_registry,
        check_interval: float | None = None,
    ):
        self._db_manager = db_manager
        self._agent_registry = agent_registry
        self._check_interval = check_interval  # None = 从 system_config 读取
        self._task: asyncio.Task | None = None
        self._running = False

    # ── 配置读取 ──────────────────────────────────────────────────────

    def _get_config(self, key: str, default):
        """从 system_config 表读取配置值"""
        try:
            from sqlalchemy import text
            with self._db_manager.engine.connect() as conn:
                row = conn.execute(
                    text("SELECT value FROM system_config WHERE category='agent' AND key=:key"),
                    {"key": key},
                ).fetchone()
            if row and row[0]:
                raw = row[0].strip('"')
                if raw.lower() == "true":
                    return True
                if raw.lower() == "false":
                    return False
                try:
                    return int(raw)
                except ValueError:
                    try:
                        return float(raw)
                    except ValueError:
                        return raw
            return default
        except Exception:
            return default

    # ── 生命周期 ──────────────────────────────────────────────────────

    async def start(self):
        """启动后台探测"""
        if self._running:
            return
        self._running = True

        # 首次读取配置
        enabled = self._get_config("agent_probe_enabled", DEFAULT_PROBE_ENABLED)
        if not enabled:
            logger.info("[AgentHealthProbe] Disabled by config, not starting")
            return

        interval = self._get_config(
            "agent_probe_interval_seconds", DEFAULT_PROBE_INTERVAL
        )
        timeout = self._get_config(
            "agent_probe_timeout_seconds", DEFAULT_PROBE_TIMEOUT
        )
        probe_path = self._get_config(
            "agent_probe_path", DEFAULT_PROBE_PATH
        )

        logger.info(
            f"[AgentHealthProbe] Started (interval={interval}s, timeout={timeout}s, path={probe_path})"
        )
        self._task = asyncio.create_task(self._run(interval, timeout, probe_path))

    async def stop(self):
        """停止后台探测"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[AgentHealthProbe] Stopped")

    # ── 探测循环 ──────────────────────────────────────────────────────

    async def _run(self, interval: float, timeout: float, probe_path: str):
        """探测主循环"""
        while self._running:
            try:
                # 每次循环重新读取配置（支持热更新）
                enabled = self._get_config("agent_probe_enabled", DEFAULT_PROBE_ENABLED)
                if not enabled:
                    logger.info("[AgentHealthProbe] Disabled by config, waiting...")
                else:
                    current_timeout = self._get_config(
                        "agent_probe_timeout_seconds", timeout
                    )
                    current_path = self._get_config("agent_probe_path", probe_path)
                    await self._probe_all_agents(current_timeout, current_path)
            except Exception as e:
                logger.error(f"[AgentHealthProbe] Probe error: {e}")

            await asyncio.sleep(interval)

    # ── 探测逻辑 ──────────────────────────────────────────────────────

    async def _probe_all_agents(self, timeout: float, probe_path: str):
        """探测所有已注册 Agent"""
        from sqlalchemy import text

        with self._db_manager.engine.connect() as conn:
            agents = conn.execute(
                text("""
                    SELECT id, name, address, status, last_heartbeat
                    FROM agents
                    WHERE health_status != 'removed'
                    ORDER BY id
                """)
            ).fetchall()

        if not agents:
            logger.debug("[AgentHealthProbe] No agents to probe")
            return

        results = {"total": len(agents), "online": 0, "offline": 0, "errors": 0}

        for agent in agents:
            result = await self._probe_single(agent.id, agent.name, agent.address, timeout, probe_path)
            if result == "online":
                results["online"] += 1
            elif result == "offline":
                results["offline"] += 1
            else:
                results["errors"] += 1

        logger.info(
            f"[AgentHealthProbe] Probe complete: {results['online']} online, "
            f"{results['offline']} offline, {results['errors']} errors"
        )

    async def _probe_single(
        self, agent_id: str, name: str, address: Optional[str],
        timeout: float, probe_path: str
    ) -> str:
        """探测单个 Agent，返回 'online' / 'offline' / 'error'"""
        from sqlalchemy import text

        if not address:
            logger.debug(f"[AgentHealthProbe] {name} ({agent_id}): no address, skipping")
            return "error"

        base_url = address.rstrip("/")
        url = f"{base_url}{probe_path}"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url)
                status_code = resp.status_code
        except httpx.ConnectError:
            status_code = 0
        except Exception as e:
            logger.debug(f"[AgentHealthProbe] {name} ({agent_id}): probe exception: {e}")
            status_code = -1

        now = datetime.now()

        if status_code > 0 and status_code < 500:
            # 在线：更新 last_heartbeat + status
            with self._db_manager.engine.begin() as conn:
                conn.execute(
                    text("""
                        UPDATE agents
                        SET last_heartbeat = :now,
                            status = 'online',
                            health_status = 'online',
                            consecutive_offline_count = 0,
                            updated_at = :now
                        WHERE id = :aid
                    """),
                    {"now": now, "aid": agent_id},
                )
            logger.debug(
                f"[AgentHealthProbe] ✅ {name} ({agent_id}): online "
                f"(HTTP {status_code} at {url})"
            )
            return "online"
        else:
            # 离线：增加 offline count，超过阈值标记 offline
            with self._db_manager.engine.connect() as conn:
                row = conn.execute(
                    text("""
                        SELECT consecutive_offline_count, max_offline_before_deactivate, status
                        FROM agents WHERE id = :aid
                    """),
                    {"aid": agent_id},
                ).fetchone()

            if row:
                current_count = row[0] or 0
                max_offline = row[2] or 3
                current_status = row[2] or "online"

                new_count = current_count + 1
                if new_count >= max_offline:
                    new_status = "offline"
                    new_count = 0  # 重置
                else:
                    new_status = current_status

                with self._db_manager.engine.begin() as conn:
                    conn.execute(
                        text("""
                            UPDATE agents
                            SET consecutive_offline_count = :count,
                                status = :status,
                                health_status = :status,
                                updated_at = :now
                            WHERE id = :aid
                        """),
                        {"count": new_count, "status": new_status, "now": now, "aid": agent_id},
                    )

            logger.debug(
                f"[AgentHealthProbe] ❌ {name} ({agent_id}): offline "
                f"(HTTP {status_code} at {url}, fail_count={current_count + 1})"
            )
            return "offline"


