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

from api.app_state import get_reins, get_db_manager
from reins.api._agents_register_routes import HeartbeatRequest
from models import Agent, Task, Goal, Project, ExecutionLog
from models import Attachment, AttachmentLink
from persistence.tables import heartbeat_logs

router = APIRouter()


@router.post("/agents/{agent_id}/heartbeat")
def heartbeat_agent(agent_id: str, body: Optional[HeartbeatRequest] = None):
    """Agent 心跳（增强版 - 返回 pending 任务）"""
    reins = get_reins()
    db = get_db_manager()
    status_dict = None
    if body:
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
        agent_row = db.query(Agent).with_entities(
            Agent.load, Agent.current_tasks, Agent.model_name, Agent.capability_tags
        ).filter(Agent.id == agent_id).first()
        if agent_row:
            _db_load, _db_ct, _db_model = agent_row[0], agent_row[1], agent_row[2]
            if agent_row[3]:
                try:
                    _db_caps = json.loads(agent_row[3])
                except Exception:
                    pass
    except Exception:
        pass

    # 写 heartbeat_logs + 更新 agents
    try:
        from reins.scheduler.heartbeat_decision import HeartbeatDecision
        decision = HeartbeatDecision(db).on_heartbeat_success(agent_id)
        decided = decision.get("new_state", "online")

        now = _dt.now()

        # 构建动态更新字段
        update_values = {
            Agent.last_heartbeat: now,
            Agent.health_status: decided,
            Agent.status: decided,
            Agent.consecutive_offline_count: decision.get("failure_count_reset", 0),
            Agent.updated_at: now,
        }

        if _db_load is not None and _db_load > 0:
            update_values[Agent.load] = _db_load
        if _db_ct is not None:
            update_values[Agent.current_tasks] = _db_ct

        # 如果心跳携带了 model_name，更新它
        if body and body.model_name:
            update_values[Agent.model_name] = body.model_name
            logger.info(f"[Heartbeat] Agent {agent_id} reporting model: {body.model_name}")

        # 如果心跳携带了 capability_tags，更新它
        if body and body.capability_tags:
            update_values[Agent.capability_tags] = json.dumps(body.capability_tags)
            logger.info(f"[Heartbeat] Agent {agent_id} reporting caps: {list(body.capability_tags.keys())}")

        raw_payload = json.dumps(body.model_dump(exclude_none=True)) if body else None

        session = db.get_session()
        try:
            session.execute(heartbeat_logs.insert().values(
                id=str(_uuid_lib.uuid4()), agent_id=agent_id, timestamp=now,
                status=decided, latency_ms=body.latency_ms if body else None,
                load=_db_load, current_tasks=_db_ct, raw_payload=raw_payload))
            session.query(Agent).filter(Agent.id == agent_id).update(update_values)
            session.commit()
        finally:
            session.close()
    except Exception as e:
        logger.warning(f"[P5-05] heartbeat log warning: {e}")

    # 查 pending 任务（改用统一上下文构建器）
    result = {"success": success}
    try:
        from reins.scheduler.task_context_builder import build_task_execution_context
        tasks = db.query(Task).with_entities(
            Task.id, Task.title, Task.description, Task.priority, Task.project_id
        ).filter(
            Task.assigned_agent == agent_id,
            Task.status.in_(['todo', 'pending', 'review_needed', 'waiting']),
        ).order_by(
            Task.priority
        ).limit(10).all()

        assigned = []
        for t in tasks:
            # 用统一构建器拿到完整的三级上下文 + 附件 + 统一 prompt
            base_url = os.environ.get("GREVER_BASE_URL", "http://127.0.0.1:8097")
            full_ctx = build_task_execution_context(t.id, db, include_attachments=True, base_url=base_url)

            goal_info = full_ctx.get("goal", {})
            project_info = full_ctx.get("project", {})
            task_info = full_ctx.get("task", {})

            assigned.append({
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "goal_id": goal_info.get("id"),
                "priority": t.priority,
                "context": {
                    "goal_info": {
                        "id": goal_info.get("id"),
                        "title": goal_info.get("title"),
                        "description": goal_info.get("description"),
                    },
                    "project_info": {
                        "id": project_info.get("id"),
                        "name": project_info.get("name"),
                        "description": project_info.get("description"),
                    },
                    "task_info": {
                        "id": task_info.get("id"),
                        "title": task_info.get("title"),
                        "description": task_info.get("description"),
                        "acceptance_criteria": task_info.get("acceptance_criteria"),
                        "dependencies": full_ctx.get("dependencies", []),
                    },
                    "attachments": full_ctx.get("attachments", []),
                    "prompt": full_ctx.get("prompt"),
                },
            })
        result["assigned_tasks"] = assigned
    except Exception as e:
        logger.warning(f"[MAK-214] heartbeat tasks warning: {e}")

    # 补充 agent 实时信息
    try:
        agent_row = db.query(Agent).with_entities(
            Agent.load, Agent.current_tasks, Agent.model_name, Agent.capability_tags
        ).filter(Agent.id == agent_id).first()
        if agent_row:
            result["agent_load"] = agent_row[0]
            result["current_tasks"] = agent_row[1]
            result["model_name"] = agent_row[2]
            if agent_row[3]:
                try:
                    result["capability_tags"] = json.loads(agent_row[3])
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


# === Agent Health Probe ===

import asyncio
import httpx

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
            from models.system_config import SystemConfig
            from reins.common.database import get_db_session
            session = get_db_session()
            try:
                config = session.query(SystemConfig).filter(
                    SystemConfig.category == 'agent',
                    SystemConfig.key == key
                ).first()
            finally:
                session.close()
            if config and config.value:
                raw = config.value.strip('"')
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
        session = self._db_manager.get_session()
        try:
            agents = session.query(Agent).with_entities(
                Agent.id, Agent.name, Agent.address, Agent.status, Agent.last_heartbeat
            ).filter(
                Agent.health_status != 'removed'
            ).all()

            if not agents:
                logger.debug("[AgentHealthProbe] No agents to probe")
                return

            results = {"total": len(agents), "online": 0, "offline": 0, "errors": 0}

            for agent in agents:
                aid, name, address, status, last_hb = agent
                result = await self._probe_single(aid, name, address, timeout, probe_path)
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
        finally:
            session.close()

    async def _probe_single(
        self, agent_id: str, name: str, address: Optional[str],
        timeout: float, probe_path: str
    ) -> str:
        """探测单个 Agent，返回 'online' / 'offline' / 'error'"""
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

        now = _dt.now()
        session = self._db_manager.get_session()
        try:
            if status_code > 0 and status_code < 500:
                # 在线：更新 last_heartbeat + status
                session.query(Agent).filter(Agent.id == agent_id).update({
                    Agent.last_heartbeat: now,
                    Agent.status: 'online',
                    Agent.health_status: 'online',
                    Agent.consecutive_offline_count: 0,
                    Agent.updated_at: now,
                })
                session.commit()
                logger.debug(
                    f"[AgentHealthProbe] ✅ {name} ({agent_id}): online "
                    f"(HTTP {status_code} at {url})"
                )
                return "online"
            else:
                # 离线：增加 offline count，超过阈值标记 offline
                agent = session.query(Agent).with_entities(
                    Agent.consecutive_offline_count, Agent.max_offline_before_deactivate, Agent.status
                ).filter(Agent.id == agent_id).first()

                if agent:
                    current_count = agent[0] or 0
                    max_offline = agent[1] or 3
                    current_status = agent[2] or "online"

                    new_count = current_count + 1
                    if new_count >= max_offline:
                        new_status = "offline"
                        new_count = 0  # 重置
                    else:
                        new_status = current_status

                    session.query(Agent).filter(Agent.id == agent_id).update({
                        Agent.consecutive_offline_count: new_count,
                        Agent.status: new_status,
                        Agent.health_status: new_status,
                        Agent.updated_at: now,
                    })
                    session.commit()

                logger.debug(
                    f"[AgentHealthProbe] ❌ {name} ({agent_id}): offline "
                    f"(HTTP {status_code} at {url}, fail_count={current_count + 1})"
                )
                return "offline"
        finally:
            session.close()