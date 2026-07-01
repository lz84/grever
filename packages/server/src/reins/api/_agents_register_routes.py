"""Agent registration & listing routes."""
import json
from datetime import datetime
from loguru import logger
from typing import List

from fastapi import APIRouter, HTTPException

from api.app_state import get_reins
"""Shared Pydantic models for agents_router submodules."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class AgentRegister(BaseModel):
    agent_id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent 名称")
    capabilities: List[str] = Field(default=[], description="能力列表（注册时传入，自动转为 capability_tags）")
    capability_tags: Optional[Dict[str, List[str]]] = Field(None, description="四维能力标签（优先使用）")
    address: Optional[str] = None
    metadata: Optional[dict] = None
    trigger_mode: Optional[str] = Field("sse", description="sse/polling")
    poll_interval_seconds: Optional[int] = Field(10)
    model_name: Optional[str] = Field("", description="使用的模型名称")
    platform_type: Optional[str] = Field("openclaw", description="平台类型（新增字段）")
    platform_config: Optional[Dict[str, Any]] = Field(None, description="平台专属配置 JSON（新增字段）")

class AgentResponse(BaseModel):
    id: str
    name: str
    capability_tags: Dict[str, List[str]] = {}
    status: str
    address: Optional[str] = None
    metadata: dict = {}
    load: int = 0
    current_tasks: int = 0
    trigger_mode: str = "sse"
    model_name: str = ""
    poll_interval_seconds: int = 10
    registered_at: str = ""
    last_heartbeat: str = ""
    platform_type: str = "openclaw"  # 新增字段
    model_config = {"from_attributes": True}

class HeartbeatRequest(BaseModel):
    status: Optional[Any] = None  # 兼容：可以是字符串（旧格式）或对象（新格式 {state, load, current_tasks}）
    state: Optional[str] = None
    load: Optional[int] = None
    current_tasks: Optional[int] = None
    latency_ms: Optional[int] = None
    model_name: Optional[str] = None  # Agent 自报模型名称
    capability_tags: Optional[Dict[str, List[str]]] = None  # Agent 自报能力标签

class CapabilityTagsUpdate(BaseModel):
    capability_tags: Dict[str, List[str]]


router = APIRouter()


# ── Sensitive field masking ──────────────────────────────────────────────
_SENSITIVE_KEYS = frozenset([
    "api_key", "secret", "secret_key", "token", "access_token",
    "private_key", "password", "credential", "auth_token", "bearer_token",
    "client_secret", "api_secret",
])

def _mask_sensitive_fields(config: dict) -> dict:
    """Replace values of sensitive keys with '***'."""
    if not config:
        return config
    return {
        k: ("***" if k.lower() in _SENSITIVE_KEYS else v)
        for k, v in config.items()
    }

def _to_iso(val):
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    return str(val)


# ── Static routes (MUST be before parameterized routes) ─────────────────

@router.post("/agents", response_model=AgentResponse)
def register_agent(agent: AgentRegister):
    """注册 Agent（自动生成 API Token）"""
    reins = get_reins()
    from models import TriggerMode
    try:
        tm = TriggerMode(agent.trigger_mode or "sse")
    except ValueError:
        tm = TriggerMode.SSE

    # Convert capabilities (legacy array) to capability_tags (new object format)
    if agent.capability_tags:
        caps_obj = agent.capability_tags
    else:
        caps_obj = {"business": [], "professional": [], "technical": agent.capabilities, "management": []}

    # Determine platform_type (default openclaw)
    platform_type = agent.platform_type or "openclaw"

    logger.debug(f"[register] agent_id={agent.agent_id} name={agent.name} "
                 f"capabilities={agent.capabilities} address={agent.address} "
                 f"metadata={agent.metadata} trigger_mode={tm}")

    a = reins.register_agent(
        agent.agent_id, agent.name,
        agent.capabilities or [],  # capabilities: list[str]
        address=agent.address,
        metadata=agent.metadata,
        trigger_mode=tm,
        poll_interval_seconds=agent.poll_interval_seconds or 10,
        model_name=agent.model_name or "",
    )

    logger.debug(f"[register] agent created: {a}")

    # If platform_type is not default 'openclaw' or has platform_config,
    # write to agents_config via direct DB (backward-compatible migration path)
    if platform_type != "openclaw" or agent.platform_config:
        _write_agents_config(agent.agent_id, platform_type, agent.platform_config or {})

    d = a.to_dict()
    d["capability_tags"] = caps_obj
    d["platform_type"] = platform_type
    resp = AgentResponse.model_validate(d)
    return resp


def _write_agents_config(agent_id: str, platform_type: str, config: dict):
    """
    写入 agents_config 表（仅当表存在时）

    幂等操作：只 INSERT 不覆盖已有记录。
    """
    import json as _json
    from reins.common.database import get_db_session
    from models.agent import AgentConfig

    try:
        session = get_db_session()
        try:
            now = datetime.now()
            existing = session.query(AgentConfig).filter(AgentConfig.agent_id == agent_id).first()
            config_json = _json.dumps(config, ensure_ascii=False) if config else "{}"

            if not existing:
                new_config = AgentConfig(
                    agent_id=agent_id,
                    platform_type=platform_type,
                    config_json=config_json,
                    created_at=now,
                )
                session.add(new_config)
            else:
                session.query(AgentConfig).filter(AgentConfig.agent_id == agent_id).update({
                    "platform_type": platform_type,
                    "config_json": config_json,
                    "updated_at": now,
                })
            session.commit()
        finally:
            session.close()
    except Exception as e:
        logger.warning(f"[_write_agents_config] Failed to write config for {agent_id}: {e}")


@router.get("/agents", response_model=List[AgentResponse])
def get_registered_agents():
    """获取已注册 Agent（列出前自动清理心跳超时的 agent）"""
    from api.app_state import get_reins
    from reins.common.database import get_db_session
    from reins.scheduler.load_calculator import calc_all_agents_load
    from models import Agent
    # 先清理心跳超时的 agent（标记为 offline）
    try:
        reins = get_reins()
        reins.agent_registry.cleanup_dead_agents()
    except Exception:
        pass  # 清理失败不影响列表展示
    session = get_db_session()
    try:
        load_map = calc_all_agents_load(session)
        rows = session.query(Agent).order_by(Agent.registered_at.desc()).all()
        return [AgentResponse(
            id=r.id, name=r.name,
            capability_tags=json.loads(r.capability_tags) if r.capability_tags else {},
            status=r.status, address=r.address,
            metadata=json.loads(r.meta_data) if r.meta_data else {},
            load=load_map.get(r.id, (0, 0))[0],
            current_tasks=load_map.get(r.id, (0, 0))[1],
            trigger_mode=r.trigger_mode or "sse",
            poll_interval_seconds=r.poll_interval_seconds or 10,
            model_name=r.model_name or "",
            registered_at=_to_iso(r.registered_at),
            last_heartbeat=_to_iso(r.last_heartbeat),
            platform_type=r.platform_type if hasattr(r, 'platform_type') else "openclaw",
        ) for r in rows]
    finally:
        session.close()


@router.get("/agents/stats")
def get_agents_stats():
    """统计各状态 Agent 数量"""
    from reins.common.database import get_db_session
    from reins.scheduler.load_calculator import calc_all_agents_load
    from models import Agent
    from sqlalchemy import func

    session = get_db_session()
    try:
        rows = session.query(Agent.status, Agent.trigger_mode, func.count(Agent.id)).group_by(
            Agent.status, Agent.trigger_mode
        ).all()

        load_map = calc_all_agents_load(session)
        total_load = sum(v[0] for v in load_map.values()) if load_map else 0
        avg_load = int(total_load / len(load_map)) if load_map else 0
        total_tasks = sum(v[1] for v in load_map.values()) if load_map else 0
    finally:
        session.close()

    total = 0
    by_status = {"online": 0, "stale": 0, "offline": 0}
    by_trigger_mode = {}
    for status, trigger, cnt in rows:
        total += cnt
        status = status or "offline"
        trigger = trigger or "sse"
        if status in by_status:
            by_status[status] += cnt
        else:
            by_status[status] = cnt
        by_trigger_mode[trigger] = by_trigger_mode.get(trigger, 0) + cnt

    return {
        "total": total,
        "online": by_status.get("online", 0),
        "stale": by_status.get("stale", 0),
        "offline": by_status.get("offline", 0),
        "by_trigger_mode": by_trigger_mode,
        "avg_load": avg_load,
        "total_tasks_in_progress": total_tasks,
    }


@router.get("/agents/online", response_model=List[AgentResponse])
def get_online_agents():
    """获取在线 Agent"""
    reins = get_reins()
    agents = reins.get_registered_agents()
    result = []
    for a in agents:
        d = a.to_dict()
        if d.get('status') != 'online':
            continue
        # AgentInfo.to_dict() 输出 capabilities，前端需要 capability_tags
        caps_raw = d.pop('capabilities', {})
        if isinstance(caps_raw, dict):
            d['capability_tags'] = caps_raw
        elif isinstance(caps_raw, list):
            d['capability_tags'] = {"business": [], "professional": [], "technical": caps_raw, "management": []}
        else:
            d['capability_tags'] = {}
        d.setdefault('trigger_mode', 'sse')
        d.setdefault('poll_interval_seconds', 10)
        result.append(AgentResponse.model_validate(d))
    return result


# ── Parameterized routes ────────────────────────────────────────────────

@router.get("/agents/{agent_id}")
def get_agent_detail(agent_id: str):
    """获取单个 Agent 详情（含配置字段）"""
    from reins.common.database import get_db_session
    from reins.scheduler.load_calculator import calc_dynamic_load
    from models import Agent
    from models.agent import AgentConfig
    session = get_db_session()
    try:
        agent = session.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        dynamic_load, dynamic_tasks = calc_dynamic_load(session, agent_id)

        # Get platform config
        platform_config = {}
        config = session.query(AgentConfig).filter(AgentConfig.agent_id == agent_id).first()
        platform_type = config.platform_type if config else "openclaw"
        if config and config.config_json:
            try:
                platform_config = json.loads(config.config_json)
            except Exception:
                platform_config = {}

        return {
            "id": agent.id,
            "name": agent.name,
            "capability_tags": json.loads(agent.capability_tags) if agent.capability_tags else {},
            "status": agent.status,
            "address": agent.address,
            "metadata": json.loads(agent.meta_data) if agent.meta_data else {},
            "load": dynamic_load,
            "current_tasks": dynamic_tasks,
            "trigger_mode": agent.trigger_mode or "sse",
            "poll_interval_seconds": agent.poll_interval_seconds or 10,
            "model_name": agent.model_name or "",
            "max_concurrent_tasks": agent.max_concurrent_tasks or 0,
            "load_threshold": agent.load_threshold or 80,
            "health_status": agent.health_status or "",
            "registered_at": _to_iso(agent.registered_at),
            "last_heartbeat": _to_iso(agent.last_heartbeat),
            "platform_type": platform_type,
            "platform_config": _mask_sensitive_fields(platform_config),
            "agent_code": agent.agent_code or None,  # OpenClaw agent code
        }
    finally:
        session.close()


@router.get("/agents/{agent_id}/tag-recommendations")
def get_tag_recommendations(agent_id: str):
    """推荐未拥有的同维度标签"""
    from reins.common.database import get_db_session
    from models import Agent

    session = get_db_session()
    try:
        agent = session.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        existing = json.loads(agent.capability_tags) if agent.capability_tags else {}
    finally:
        session.close()

    # 预定义的推荐标签池（按维度）
    tag_pool = {
        "business": ["数据分析", "内容创作", "用户服务", "市场调研", "产品管理",
                      "销售支持", "运营优化", "客户成功", "战略规划", "竞品分析"],
        "professional": ["代码审查", "架构设计", "API 开发", "数据库优化", "DevOps",
                          "安全审计", "性能调优", "测试自动化", "文档编写", "技术分享"],
        "technical": ["Python", "TypeScript", "Go", "Rust", "SQL",
                       "Docker", "Kubernetes", "CI/CD", "LLM", "RAG"],
        "management": ["项目协调", "团队协作", "进度跟踪", "风险管理", "质量保障",
                        "资源分配", "决策支持", "知识管理", "流程优化", "跨部门协作"],
    }

    # 推荐 = tag_pool 中每个维度下，不在 existing 中的标签（取前 5 个）
    recommendations = {}
    for dim, pool in tag_pool.items():
        owned = set(existing.get(dim, []))
        recommendations[dim] = [t for t in pool if t not in owned][:5]

    return {
        "agent_id": agent_id,
        "existing_tags": existing,
        "recommendations": recommendations,
    }


@router.put("/agents/{agent_id}/capability-tags")
def update_agent_capability_tags(agent_id: str, body: CapabilityTagsUpdate):
    """更新 Agent 能力标签"""
    from reins.common.database import get_db_session
    from models import Agent

    session = get_db_session()
    try:
        agent = session.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        session.query(Agent).filter(Agent.id == agent_id).update({
            "capability_tags": json.dumps(body.capability_tags, ensure_ascii=False),
        })
        session.commit()
    finally:
        session.close()

    return {
        "agent_id": agent_id,
        "capability_tags": body.capability_tags,
    }


@router.delete("/agents/{agent_id}")
def unregister_agent_route(agent_id: str, reason: str = None):
    """真正从 DB 删除 Agent"""
    from reins.common.database import get_db_session
    from models import Agent
    session = get_db_session()
    try:
        result = session.query(Agent).filter(Agent.id == agent_id).delete()
        session.commit()
        return {"success": result > 0}
    finally:
        session.close()

