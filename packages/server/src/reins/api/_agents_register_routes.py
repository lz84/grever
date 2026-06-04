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

    print(f"[DEBUG register] agent_id={agent.agent_id} name={agent.name} "
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

    print(f"[DEBUG register] agent created: {a}")

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
    import sqlalchemy as sa
    from sqlalchemy import text
    from api.app_state import get_db_manager

    try:
        db = get_db_manager()
        now = datetime.now()
        with db.engine.begin() as conn:
            # Check if agents_config table exists
            table_exists = conn.execute(text(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='agents_config'"
            )).scalar()
            if not table_exists:
                return  # Table not created yet, skip

            # Check if record already exists
            exists = conn.execute(text(
                "SELECT 1 FROM agents_config WHERE agent_id = :aid"
            ), {"aid": agent_id}).fetchone()

            import json as _json
            config_json = _json.dumps(config, ensure_ascii=False) if config else "{}"

            if not exists:
                conn.execute(text(
                    "INSERT INTO agents_config (agent_id, platform_type, config_json, created_at) "
                    "VALUES (:agent_id, :platform_type, :config_json, :created_at)"
                ), {
                    "agent_id": agent_id,
                    "platform_type": platform_type,
                    "config_json": config_json,
                    "created_at": now,
                })
            else:
                conn.execute(text(
                    "UPDATE agents_config SET platform_type=:platform_type, "
                    "config_json=:config_json, updated_at=:updated_at "
                    "WHERE agent_id=:agent_id"
                ), {
                    "agent_id": agent_id,
                    "platform_type": platform_type,
                    "config_json": config_json,
                    "updated_at": now,
                })
    except Exception as e:
        logger.warning(f"[_write_agents_config] Failed to write config for {agent_id}: {e}")


@router.get("/agents", response_model=List[AgentResponse])
def get_registered_agents():
    """获取已注册 Agent（列出前自动清理心跳超时的 agent）"""
    from api.app_state import get_db_manager, get_reins
    from reins.scheduler.load_calculator import calc_all_agents_load
    from sqlalchemy import text
    # 先清理心跳超时的 agent（标记为 offline）
    try:
        reins = get_reins()
        reins.agent_registry.cleanup_dead_agents()
    except Exception:
        pass  # 清理失败不影响列表展示
    db = get_db_manager()
    with db.engine.connect() as conn:
        load_map = calc_all_agents_load(conn)
        rows = conn.execute(text(
            "SELECT a.id, a.name, a.capability_tags, a.status, a.address, a.metadata, "
            "a.trigger_mode, a.poll_interval_seconds, a.model_name, "
            "a.registered_at, a.last_heartbeat, "
            "COALESCE(ac.platform_type, 'openclaw') as platform_type "
            "FROM agents a "
            "LEFT JOIN agents_config ac ON a.id = ac.agent_id "
            "ORDER BY a.registered_at DESC"
        )).fetchall()
    return [AgentResponse(
        id=r.id, name=r.name,
        capability_tags=json.loads(r.capability_tags) if r.capability_tags else {},
        status=r.status, address=r.address,
        metadata=json.loads(r.metadata) if r.metadata else {},
        load=load_map.get(r.id, (0, 0))[0],
        current_tasks=load_map.get(r.id, (0, 0))[1],
        trigger_mode=r.trigger_mode or "sse",
        poll_interval_seconds=r.poll_interval_seconds or 10,
        model_name=r.model_name or "",
        registered_at=_to_iso(r.registered_at),
        last_heartbeat=_to_iso(r.last_heartbeat),
        platform_type=r.platform_type or "openclaw",
    ) for r in rows]


@router.get("/agents/stats")
def get_agents_stats():
    """统计各状态 Agent 数量"""
    from api.app_state import get_db_manager
    from reins.scheduler.load_calculator import calc_all_agents_load
    from sqlalchemy import text

    db = get_db_manager()
    with db.engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT status, trigger_mode, "
            "COUNT(*) as cnt "
            "FROM agents GROUP BY status, trigger_mode"
        )).fetchall()

        # Calculate load and tasks
        load_map = calc_all_agents_load(conn)
        total_load = sum(v[0] for v in load_map.values()) if load_map else 0
        avg_load = int(total_load / len(load_map)) if load_map else 0
        total_tasks = sum(v[1] for v in load_map.values()) if load_map else 0

    total = 0
    by_status = {"online": 0, "stale": 0, "offline": 0}
    by_trigger_mode = {}
    for r in rows:
        cnt = r.cnt
        total += cnt
        status = r.status or "offline"
        trigger = r.trigger_mode or "sse"
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
    from api.app_state import get_db_manager
    from reins.scheduler.load_calculator import calc_dynamic_load
    from sqlalchemy import text
    db = get_db_manager()
    with db.engine.connect() as conn:
        row = conn.execute(text(
            "SELECT a.id, a.name, a.capability_tags, a.status, a.address, a.metadata, "
            "a.trigger_mode, a.poll_interval_seconds, "
            "a.model_name, a.registered_at, a.last_heartbeat, a.max_concurrent_tasks, "
            "a.load_threshold, a.health_status, "
            "COALESCE(ac.platform_type, 'openclaw') as platform_type, "
            "ac.config_json "
            "FROM agents a "
            "LEFT JOIN agents_config ac ON a.id = ac.agent_id "
            "WHERE a.id = :id"
        ), {"id": agent_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
        dynamic_load, dynamic_tasks = calc_dynamic_load(conn, agent_id)

        # 解析 platform_config
        platform_config = {}
        if row.config_json:
            try:
                platform_config = json.loads(row.config_json)
            except Exception:
                platform_config = {}

        return {
            "id": row.id,
            "name": row.name,
            "capability_tags": json.loads(row.capability_tags) if row.capability_tags else {},
            "status": row.status,
            "address": row.address,
            "metadata": json.loads(row.metadata) if row.metadata else {},
            "load": dynamic_load,
            "current_tasks": dynamic_tasks,
            "trigger_mode": row.trigger_mode or "sse",
            "poll_interval_seconds": row.poll_interval_seconds or 10,
            "model_name": row.model_name or "",
            "max_concurrent_tasks": row.max_concurrent_tasks or 0,
            "load_threshold": row.load_threshold or 80,
            "health_status": row.health_status or "",
            "registered_at": _to_iso(row.registered_at),
            "last_heartbeat": _to_iso(row.last_heartbeat),
            "platform_type": row.platform_type,
            "platform_config": _mask_sensitive_fields(platform_config),
        }


@router.get("/agents/{agent_id}/tag-recommendations")
def get_tag_recommendations(agent_id: str):
    """推荐未拥有的同维度标签"""
    from api.app_state import get_db_manager
    from sqlalchemy import text
    import json as _json

    db = get_db_manager()
    with db.engine.connect() as conn:
        row = conn.execute(text(
            "SELECT capability_tags FROM agents WHERE id = :aid"
        ), {"aid": agent_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")

        existing = _json.loads(row.capability_tags) if row.capability_tags else {}

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
    from api.app_state import get_db_manager
    from sqlalchemy import text
    import json as _json

    db = get_db_manager()
    with db.engine.begin() as conn:
        # Check agent exists
        row = conn.execute(text("SELECT id FROM agents WHERE id = :aid"), {"aid": agent_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")

        conn.execute(text(
            "UPDATE agents SET capability_tags = :tags WHERE id = :aid"
        ), {
            "aid": agent_id,
            "tags": _json.dumps(body.capability_tags, ensure_ascii=False),
        })

    return {
        "agent_id": agent_id,
        "capability_tags": body.capability_tags,
    }


@router.delete("/agents/{agent_id}")
def unregister_agent_route(agent_id: str, reason: str = None):
    """真正从 DB 删除 Agent"""
    from api.app_state import get_db_manager
    from sqlalchemy import text
    db = get_db_manager()
    with db.engine.begin() as conn:
        result = conn.execute(text("DELETE FROM agents WHERE id = :aid"), {"aid": agent_id})
        return {"success": result.rowcount > 0}
