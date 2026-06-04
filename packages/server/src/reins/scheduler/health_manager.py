"""
Agent 健康度管理

Phase 2: 实现 AgentHealthManager 类
- scan(): 扫描所有 Agent，更新健康状态
- on_heartbeat(): 收到心跳时恢复健康状态
- get_offline_agents(): 获取离线 Agent 列表
- get_stale_agents(): 获取 stale Agent 列表
"""
from loguru import logger

from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy import text

class AgentHealthManager:
    """
    Agent 健康度管理器
    
    健康状态定义：
    - online: last_heartbeat < STALE_THRESHOLD (5分钟)
    - stale: STALE_THRESHOLD <= last_heartbeat < OFFLINE_THRESHOLD (5-15分钟)
    - offline: last_heartbeat >= OFFLINE_THRESHOLD (>=15分钟)
    """

    # 健康度阈值（秒）
    STALE_THRESHOLD = 300      # 5 分钟无心跳 → stale
    OFFLINE_THRESHOLD = 900    # 15 分钟无心跳 → offline

    def __init__(self, db_manager):
        self.db = db_manager

    def scan(self) -> Dict[str, Any]:
        """
        扫描所有 Agent，更新健康状态
        
        返回：
        - online_count: 在线 Agent 数量
        - stale_count: stale Agent 数量
        - offline_count: 离线 Agent 数量
        """
        now = datetime.now()
        stale_cutoff = now - timedelta(seconds=self.STALE_THRESHOLD)
        offline_cutoff = now - timedelta(seconds=self.OFFLINE_THRESHOLD)

        try:
            with self.db.engine.connect() as conn:
                # 标记 offline agents (last_heartbeat < offline_cutoff)
                conn.execute(text("""
                    UPDATE agents
                    SET health_status = 'offline',
                        updated_at = :now
                    WHERE health_status != 'offline'
                      AND last_heartbeat < :offline_cutoff
                """), {
                    "now": now,
                    "offline_cutoff": offline_cutoff
                })

                # 标记 stale agents (offline_cutoff <= last_heartbeat < stale_cutoff)
                conn.execute(text("""
                    UPDATE agents
                    SET health_status = 'stale',
                        updated_at = :now
                    WHERE health_status = 'online'
                      AND last_heartbeat >= :offline_cutoff
                      AND last_heartbeat < :stale_cutoff
                """), {
                    "now": now,
                    "offline_cutoff": offline_cutoff,
                    "stale_cutoff": stale_cutoff
                })

                # 标记 online agents (last_heartbeat >= stale_cutoff)
                conn.execute(text("""
                    UPDATE agents
                    SET health_status = 'online',
                        updated_at = :now
                    WHERE health_status IN ('stale', 'offline')
                      AND last_heartbeat >= :stale_cutoff
                """), {
                    "now": now,
                    "stale_cutoff": stale_cutoff
                })

                # 统计结果
                result = conn.execute(text("""
                    SELECT 
                        SUM(CASE WHEN health_status = 'online' THEN 1 ELSE 0 END) as online,
                        SUM(CASE WHEN health_status = 'stale' THEN 1 ELSE 0 END) as stale,
                        SUM(CASE WHEN health_status = 'offline' THEN 1 ELSE 0 END) as offline
                    FROM agents
                """)).fetchone()

                conn.commit()

                return {
                    "online_count": result[0] or 0,
                    "stale_count": result[1] or 0,
                    "offline_count": result[2] or 0,
                }
        except Exception as e:
            logger.error(f"[HealthManager] Scan error: {e}")
            return {"online_count": 0, "stale_count": 0, "offline_count": 0}

    def on_heartbeat(self, agent_id: str) -> bool:
        """
        Agent 心跳时恢复健康状态
        
        如果 agent 处于 stale/offline 状态，收到心跳后恢复为 online
        """
        try:
            with self.db.engine.connect() as conn:
                result = conn.execute(text("""
                    UPDATE agents
                    SET health_status = 'online',
                        updated_at = :now
                    WHERE id = :agent_id
                      AND health_status != 'online'
                """), {
                    "agent_id": agent_id,
                    "now": datetime.now()
                })
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"[HealthManager] on_heartbeat error for {agent_id}: {e}")
            return False

    def get_offline_agents(self) -> List[str]:
        """获取所有离线 Agent ID 列表"""
        try:
            with self.db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id FROM agents WHERE health_status = 'offline'
                """)).fetchall()
                return [row[0] for row in result]
        except Exception as e:
            logger.error(f"[HealthManager] get_offline_agents error: {e}")
            return []

    def get_stale_agents(self) -> List[str]:
        """获取所有 stale Agent ID 列表"""
        try:
            with self.db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id FROM agents WHERE health_status = 'stale'
                """)).fetchall()
                return [row[0] for row in result]
        except Exception as e:
            logger.error(f"[HealthManager] get_stale_agents error: {e}")
            return []
