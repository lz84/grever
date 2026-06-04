"""
Agent 注册 (Agent Registration) - DB 驱动版
所有数据源自数据库，不使用内存缓存

改造要点：
- 移除 self._agents 内存字典
- 所有操作直接读写数据库
- AgentInfo 对象仅作为返回值使用（非缓存）
"""

from typing import List, Optional
from models import AgentInfo, AgentStatus, TriggerMode
from datetime import datetime, timedelta
from sqlalchemy import text
import json
from loguru import logger

class AgentRegistry:
    """
    Agent 注册管理器（DB 驱动）

    注意：所有数据操作直接走数据库，不使用内存缓存。
    AgentInfo 对象仅作为返回值使用。
    """

    # 心跳超时时间（秒）—— Agent 超过此时间无心跳则标记为 offline
    HEARTBEAT_TIMEOUT = 600  # 10 分钟（OpenClaw agent 仅在任务派发时心跳，非实时心跳）

    def __init__(self, get_db_session=None):
        """
        Args:
            get_db_session: 获取 DB session 的函数。如果为 None，会从 reins.database 导入。
        """
        self._get_db = get_db_session
        if self._get_db is None:
            from reins.common.database import get_db_session
            self._get_db = get_db_session

    def _db(self):
        """获取数据库连接"""
        conn = self._get_db()
        return conn

    # ==================== 内部工具方法 ====================

    def _row_to_agent(self, row) -> AgentInfo:
        """将 DB row 转为 AgentInfo 对象"""
        if isinstance(row, dict):
            data = row
        elif hasattr(row, '_mapping'):
            data = dict(row._mapping)
        else:
            data = dict(row) if hasattr(row, '__iter__') else {}

        # 解析 capability_tags JSON
        caps = data.get('capability_tags', data.get('capabilities', '{}'))
        if isinstance(caps, str):
            try:
                caps = json.loads(caps)
            except (json.JSONDecodeError, TypeError):
                caps = {}
        if isinstance(caps, list):
            caps = {"business": [], "professional": [], "technical": caps, "management": []}

        # 解析 metadata JSON
        meta = data.get('metadata', '{}')
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                meta = {}

        # 解析状态字符串
        status_str = data.get('status', 'offline')
        try:
            status = AgentStatus(status_str)
        except (ValueError, TypeError):
            status = AgentStatus.OFFLINE

        # 解析 trigger_mode
        trigger_mode = data.get('trigger_mode', 'sse')
        if isinstance(trigger_mode, str):
            try:
                trigger_mode = TriggerMode(trigger_mode)
            except (ValueError, TypeError):
                trigger_mode = TriggerMode.SSE

        # 解析时间
        def parse_dt(val):
            if val is None:
                return datetime.now()
            if isinstance(val, datetime):
                return val
            try:
                return datetime.fromisoformat(str(val))
            except (ValueError, TypeError):
                return datetime.now()

        return AgentInfo(
            id=str(data.get('id', '')),
            name=str(data.get('name', '')),
            capabilities=caps,
            status=status,
            address=data.get('address'),
            metadata=meta,
            load=int(data.get('load', 0) or 0),
            current_load=int(data.get('load', 0) or 0),  # 兼容 assignment.py
            current_tasks=int(data.get('current_tasks', 0) or 0),
            trigger_mode=trigger_mode,
            poll_interval_seconds=int(data.get('poll_interval_seconds', 10) or 10),
            model_name=str(data.get('model_name', '')),
            registered_at=parse_dt(data.get('registered_at')),
            last_heartbeat=parse_dt(data.get('last_heartbeat')),
        )

    # ==================== 公开方法 ====================

    def register(
        self,
        agent_id: str,
        name: str,
        capabilities: List[str],
        address: str = None,
        metadata: dict = None,
        trigger_mode: TriggerMode = TriggerMode.SSE,
        poll_interval_seconds: int = 10,
        model_name: str = "",
        last_heartbeat: "datetime" = None,
    ) -> AgentInfo:
        """
        注册 Agent（UPSERT：存在则更新，不存在则插入）
        
        last_heartbeat: 可选，传入 DB 中已有的 heartbeat 以避免被覆盖。
        用于 server 重启后同步，避免 HeartbeatOfflineDetector 误判。
        """
        now = datetime.now()
        tm = trigger_mode.value if isinstance(trigger_mode, TriggerMode) else trigger_mode
        
        # 如果传入了已有的 heartbeat，用它；否则用当前时间
        hb = last_heartbeat if last_heartbeat else now

        conn = self._db()
        # 先检查是否存在
        existing = conn.execute(text(
            "SELECT id FROM agents WHERE id = :aid"
        ), {"aid": agent_id}).fetchone()

        if existing:
            # UPDATE
            # Convert old array format to new object format if needed
            if isinstance(capabilities, list):
                cap_json = json.dumps({
                    "business": [], "professional": [],
                    "technical": capabilities, "management": []
                })
            else:
                cap_json = capabilities if isinstance(capabilities, str) else json.dumps(capabilities or {})
            conn.execute(text("""
                UPDATE agents
                SET name = :name,
                    capability_tags = :caps,
                    address = :addr,
                    metadata = :meta,
                    last_heartbeat = :hb,
                    status = :status,
                    trigger_mode = :tm,
                    poll_interval_seconds = :poll,
                    model_name = :model,
                    updated_at = :now
                WHERE id = :aid
            """), {
                "aid": agent_id,
                "name": name,
                "caps": cap_json,
                "addr": address or "",
                "meta": json.dumps(metadata or {}),
                "hb": hb,
                "status": AgentStatus.ONLINE.value,
                "tm": tm,
                "poll": poll_interval_seconds,
                "model": model_name,
                "now": now,
            })
        else:
            # INSERT
            # Convert old array format to new object format if needed
            if isinstance(capabilities, list):
                cap_json = json.dumps({
                    "business": [], "professional": [],
                    "technical": capabilities, "management": []
                })
            else:
                cap_json = capabilities if isinstance(capabilities, str) else json.dumps(capabilities or {})
            conn.execute(text("""
                INSERT INTO agents (id, name, capability_tags, status, address, metadata,
                    load, current_tasks, registered_at, last_heartbeat,
                    trigger_mode, poll_interval_seconds, model_name, updated_at)
                VALUES (:aid, :name, :caps, :status, :addr, :meta,
                    0, 0, :now, :hb, :tm, :poll, :model, :now)
            """), {
                "aid": agent_id,
                "name": name,
                "caps": cap_json,
                "status": AgentStatus.ONLINE.value,
                "addr": address or "",
                "meta": json.dumps(metadata or {}),
                "now": now,
                "hb": hb,
                "tm": tm,
                "poll": poll_interval_seconds,
                "model": model_name,
            })
        conn.commit()

        # 返回 AgentInfo（DB 已是最新的）
        row = conn.execute(text(
            "SELECT * FROM agents WHERE id = :aid"
        ), {"aid": agent_id}).fetchone()
        return self._row_to_agent(row) if row else None

    def unregister(self, agent_id: str, reason: str = None) -> bool:
        """
        注销 Agent（更新状态为 offline，不从 DB 删除）
        """
        conn = self._db()
        now = datetime.now()
        meta_update = {
            "unregister_reason": reason,
            "unregistered_at": now.isoformat(),
        }
        conn.execute(text("""
            UPDATE agents
            SET status = :status,
                metadata = json_patch(COALESCE(metadata, '{}'), :meta),
                updated_at = :now
            WHERE id = :aid
        """), {
            "aid": agent_id,
            "status": AgentStatus.OFFLINE.value,
            "meta": json.dumps(meta_update),
            "now": now,
        })
        conn.commit()
        return conn.execute(text("SELECT changes()")).fetchone()[0] > 0

    def heartbeat(self, agent_id: str, status: dict = None) -> bool:
        """
        Agent 心跳（更新 last_heartbeat 和负载信息）
        """
        conn = self._db()
        now = datetime.now()

        # 检查 agent 是否存在
        existing = conn.execute(text(
            "SELECT id, status FROM agents WHERE id = :aid"
        ), {"aid": agent_id}).fetchone()
        if not existing:
            return False

        # 更新心跳和负载
        updates = {
            "last_heartbeat": now,
            "status": AgentStatus.ONLINE.value,  # 心跳默认在线
            "now": now,
            "aid": agent_id,
        }

        if status:
            if "load" in status:
                updates["load"] = int(status["load"])
            if "current_tasks" in status:
                updates["current_tasks"] = int(status["current_tasks"])
            # _force_online: 心跳成功即在线，忽略 state 映射
            if "_force_online" not in status:
                if "state" in status:
                    state = status["state"].lower()
                    status_map = {
                        "online": AgentStatus.ONLINE.value,
                        "busy": AgentStatus.BUSY.value,
                        "idle": AgentStatus.IDLE.value,
                        "offline": AgentStatus.OFFLINE.value,
                    }
                    updates["status"] = status_map.get(state, AgentStatus.IDLE.value)

        if "load" not in updates:
            # 保留当前负载值
            current = conn.execute(text(
                "SELECT load FROM agents WHERE id = :aid"
            ), {"aid": agent_id}).fetchone()
            updates["load"] = current[0] if current else 0

        if "current_tasks" not in updates:
            current = conn.execute(text(
                "SELECT current_tasks FROM agents WHERE id = :aid"
            ), {"aid": agent_id}).fetchone()
            updates["current_tasks"] = current[0] if current else 0

        # Phase 1.1: 自动计算 load = min(100, current_tasks / max_concurrent_tasks * 100)
        max_concurrent = conn.execute(text(
            "SELECT max_concurrent_tasks FROM agents WHERE id = :aid"
        ), {"aid": agent_id}).fetchone()
        max_ct = max_concurrent[0] if max_concurrent else 5
        if max_ct > 0 and "load" not in updates:
            updates["load"] = min(100, int(updates["current_tasks"] / max_ct * 100))

        # Phase 1.3: health_status 与 status 永远保持一致
        updates["health_status"] = updates["status"]

        # Phase 1.6: 从心跳中提取 model_name 并更新
        model_name = None
        if status and status.get("model_name"):
            model_name = status["model_name"]
        elif status and status.get("model"):
            model_name = status["model"]

        # 构建 UPDATE 语句
        set_clauses = [
            "last_heartbeat = :last_heartbeat",
            "status = :status",
            "load = :load",
            "current_tasks = :current_tasks",
            "health_status = :health_status",
            "updated_at = :now",
        ]
        if model_name:
            set_clauses.append("model_name = :model_name")
            updates["model_name"] = model_name

        conn.execute(text(f"""
            UPDATE agents
            SET {', '.join(set_clauses)}
            WHERE id = :aid
        """), updates)
        conn.commit()
        return True

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """
        获取 Agent 信息（从 DB 查询）
        """
        conn = self._db()
        row = conn.execute(text(
            "SELECT * FROM agents WHERE id = :aid"
        ), {"aid": agent_id}).fetchone()
        return self._row_to_agent(row) if row else None

    def list_agents(self, status: AgentStatus = None) -> List[AgentInfo]:
        """
        列出已注册 Agent（列出前自动清理心跳超时的 agent）
        """
        # 先清理心跳超时的 agent（标记为 offline）
        self.cleanup_dead_agents()

        conn = self._db()
        if status:
            rows = conn.execute(text(
                "SELECT * FROM agents WHERE status = :status ORDER BY name"
            ), {"status": status.value}).fetchall()
        else:
            rows = conn.execute(text(
                "SELECT * FROM agents ORDER BY name"
            )).fetchall()
        return [self._row_to_agent(row) for row in rows]

    def update_status(self, agent_id: str, status: AgentStatus) -> AgentInfo:
        """
        更新 Agent 状态
        """
        conn = self._db()
        conn.execute(text("""
            UPDATE agents SET status = :status, last_heartbeat = :now, updated_at = :now
            WHERE id = :aid
        """), {
            "aid": agent_id,
            "status": status.value,
            "now": datetime.now(),
        })
        conn.commit()
        return self.get_agent(agent_id)

    def update_capabilities(self, agent_id: str, capabilities: List[str]) -> AgentInfo:
        """
        更新 Agent 能力
        """
        conn = self._db()
        cap_json = json.dumps({
            "business": [], "professional": [],
            "technical": capabilities, "management": []
        })
        conn.execute(text("""
            UPDATE agents SET capability_tags = :caps, updated_at = :now
            WHERE id = :aid
        """), {
            "aid": agent_id,
            "caps": cap_json,
            "now": datetime.now(),
        })
        conn.commit()
        return self.get_agent(agent_id)

    def update_load(self, agent_id: str, load: int, current_tasks: int = None) -> AgentInfo:
        """
        更新 Agent 负载
        """
        conn = self._db()
        load = max(0, min(100, load))

        # 根据负载自动调整状态
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        new_status = agent.status
        if load >= 80:
            new_status = AgentStatus.BUSY
        elif load < 50 and (current_tasks is None or current_tasks == 0):
            new_status = AgentStatus.IDLE
        elif agent.status == AgentStatus.BUSY and load < 70:
            new_status = AgentStatus.ONLINE

        updates = {
            "aid": agent_id,
            "load": load,
            "status": new_status.value,
            "now": datetime.now(),
        }
        if current_tasks is not None:
            updates["current_tasks"] = current_tasks

        conn.execute(text("""
            UPDATE agents
            SET load = :load, status = :status, updated_at = :now
            """ + (", current_tasks = :current_tasks" if current_tasks is not None else "") + """
            WHERE id = :aid
        """), updates)
        conn.commit()
        return self.get_agent(agent_id)

    def increment_load(self, agent_id: str) -> Optional[AgentInfo]:
        """增加负载计数（任务派发时用）"""
        conn = self._db()
        conn.execute(text("""
            UPDATE agents SET load = MIN(100, load + 1), updated_at = :now WHERE id = :aid
        """), {"aid": agent_id, "now": datetime.now()})
        conn.commit()
        return self.get_agent(agent_id)

    def decrement_load(self, agent_id: str) -> Optional[AgentInfo]:
        """减少负载计数（任务完成时用）"""
        conn = self._db()
        conn.execute(text("""
            UPDATE agents SET load = MAX(0, load - 1), updated_at = :now WHERE id = :aid
        """), {"aid": agent_id, "now": datetime.now()})
        conn.commit()
        return self.get_agent(agent_id)

    def set_load(self, agent_id: str, load: int) -> Optional[AgentInfo]:
        """设置 Agent 负载（TaskAssigner 用）"""
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        conn = self._db()
        conn.execute(text("""
            UPDATE agents SET load = :load, current_tasks = :load, updated_at = :now WHERE id = :aid
        """), {"aid": agent_id, "load": max(0, min(100, load)), "now": datetime.now()})
        conn.commit()
        return self.get_agent(agent_id)

    def calculate_load(self, current_tasks: int, max_concurrent_tasks: int) -> int:
        """
        计算 Agent 负载百分比（Phase 1.1）
        
        load = min(100, current_tasks / max_concurrent_tasks * 100)
        
        Args:
            current_tasks: 当前任务数
            max_concurrent_tasks: 最大并发任务数
            
        Returns:
            负载百分比 (0-100)
        """
        if max_concurrent_tasks <= 0:
            return 0
        return min(100, int(current_tasks / max_concurrent_tasks * 100))

    def update_load_withCalculation(self, agent_id: str, current_tasks: int = None, max_concurrent_tasks: int = None) -> Optional[AgentInfo]:
        """
        更新 Agent 负载（自动根据 current_tasks 和 max_concurrent_tasks 计算 load）
        
        Phase 1.1: load = min(100, current_tasks / max_concurrent_tasks * 100)
        
        Args:
            agent_id: Agent ID
            current_tasks: 当前任务数（可选，不传则从 DB 读取）
            max_concurrent_tasks: 最大并发任务数（可选，不传则从 DB 读取）
            
        Returns:
            更新后的 AgentInfo
        """
        conn = self._db()
        
        # 获取当前值（如果未传入）
        if current_tasks is None or max_concurrent_tasks is None:
            row = conn.execute(text("SELECT current_tasks, max_concurrent_tasks FROM agents WHERE id = :aid"), {"aid": agent_id}).fetchone()
            if not row:
                return None
            if current_tasks is None:
                current_tasks = row[0] if row[0] is not None else 0
            if max_concurrent_tasks is None:
                max_concurrent_tasks = row[1] if row[1] is not None else 5
        
        # 计算负载
        load = self.calculate_load(current_tasks, max_concurrent_tasks)
        
        # 更新数据库
        conn.execute(text("""
            UPDATE agents SET load = :load, current_tasks = :current_tasks, updated_at = :now WHERE id = :aid
        """), {
            "aid": agent_id,
            "load": load,
            "current_tasks": current_tasks,
            "now": datetime.now(),
        })
        conn.commit()
        
        return self.get_agent(agent_id)

    def is_alive(self, agent_id: str) -> bool:
        """检查 Agent 是否存活（心跳未超时）"""
        agent = self.get_agent(agent_id)
        if not agent:
            return False
        elapsed = (datetime.now() - agent.last_heartbeat).total_seconds()
        return elapsed < self.HEARTBEAT_TIMEOUT

    def get_dead_agents(self) -> List[AgentInfo]:
        """获取已超时的 Agent"""
        conn = self._db()
        threshold = datetime.now() - timedelta(seconds=self.HEARTBEAT_TIMEOUT)
        rows = conn.execute(text("""
            SELECT * FROM agents
            WHERE status IN ('online', 'busy', 'idle')
              AND last_heartbeat < :threshold
        """), {"threshold": threshold}).fetchall()
        return [self._row_to_agent(row) for row in rows]

    def cleanup_dead_agents(self) -> int:
        """清理已死亡的 Agent（标记为 offline）"""
        dead = self.get_dead_agents()
        if not dead:
            return 0
        conn = self._db()
        conn.execute(text("""
            UPDATE agents SET status = :status, updated_at = :now
            WHERE status IN ('online', 'busy', 'idle')
              AND last_heartbeat < :threshold
        """), {
            "status": AgentStatus.OFFLINE.value,
            "now": datetime.now(),
            "threshold": datetime.now() - timedelta(seconds=self.HEARTBEAT_TIMEOUT),
        })
        conn.commit()
        return len(dead)

    def get_available_agents(self) -> List[AgentInfo]:
        """获取可用的 Agent（在线且负载未满）"""
        conn = self._db()
        rows = conn.execute(text("""
            SELECT * FROM agents
            WHERE status IN ('online', 'idle')
              AND load < 80
            ORDER BY load ASC
        """)).fetchall()
        return [self._row_to_agent(row) for row in rows]

    def get_agents_by_capabilities(self, capabilities: List[str], require_all: bool = True) -> List[AgentInfo]:
        """按能力筛选 Agent"""
        # 获取所有在线 agent
        agents = self.list_agents()
        result = []
        for agent in agents:
            if agent.status in (AgentStatus.OFFLINE,):
                continue
            agent_caps = set(agent.capabilities)
            needed = set(capabilities)
            if require_all:
                if needed.issubset(agent_caps):
                    result.append(agent)
            else:
                if needed.intersection(agent_caps):
                    result.append(agent)
        return result

    def get_stats(self) -> dict:
        """获取注册统计"""
        conn = self._db()
        rows = conn.execute(text("""
            SELECT status, COUNT(*) as cnt,
                   AVG(load) as avg_load,
                   AVG(current_tasks) as avg_tasks
            FROM agents
            GROUP BY status
        """)).fetchall()

        stats = {"total": 0, "online": 0, "busy": 0, "idle": 0, "offline": 0, "dead": 0, "avg_load": 0, "avg_current_tasks": 0}
        for row in rows:
            status = row[0]
            cnt = row[1]
            stats["total"] += cnt
            if status in stats:
                stats[status] = cnt

        # 计算死亡 agent
        stats["dead"] = len(self.get_dead_agents())

        # 平均负载
        all_agents = conn.execute(text(
            "SELECT AVG(load), AVG(current_tasks) FROM agents WHERE status IN ('online', 'idle', 'busy')"
        )).fetchone()
        if all_agents and all_agents[0] is not None:
            stats["avg_load"] = all_agents[0]
            stats["avg_current_tasks"] = all_agents[1]

        return stats
