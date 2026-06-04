"""
心跳状态决策逻辑 - Phase 1.2

功能：
1. 基于连通性（last_heartbeat）+ 任务数（current_tasks）决定 Agent 状态
2. 状态分为：online/busy/offline 三种
3. 连续失败/离线计数，超过阈值标记为 offline
"""
from loguru import logger

from datetime import datetime, timedelta
from typing import Tuple, Optional
from sqlalchemy import text

# 状态阈值配置（秒）
HEARTBEAT_ONLINE_THRESHOLD = 60       # 60秒内有心跳 → online
HEARTBEAT_BUSY_THRESHOLD = 120        # 120秒内有心跳且有任务 → busy
HEARTBEAT_OFFLINE_THRESHOLD = 300     # 300秒无心跳 → offline

# 连续失败阈值
MAX_CONSECUTIVE_FAILURES = 3

class HeartbeatDecision:
    """
    心跳状态决策器
    
    决策逻辑：
    1. 连通性判断（基于 last_heartbeat）
       - online: last_heartbeat < ONLINE_THRESHOLD (60秒)
       - busy: ONLINE_THRESHOLD <= last_heartbeat < BUSY_THRESHOLD (60-120秒) 且 current_tasks > 0
       - offline: last_heartbeat >= OFFLINE_THRESHOLD (>=300秒) 或无心跳
    
    2. 任务数判断（基于 current_tasks）
       - online: current_tasks = 0 且连通性正常
       - busy: current_tasks > 0 且连通性正常
       - offline: 连通性异常
    
    3. 连续失败处理
       - 每次离线/失败时增加 consecutive_offline_count
       - 达到阈值时标记为 offline 并停止任务分配
    """
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def decide_state(self, agent_id: str) -> Tuple[str, int]:
        """
        决策 Agent 状态
        
        Args:
            agent_id: Agent ID
            
        Returns:
            (state, consecutive_failures)
            - state: 'online' | 'busy' | 'offline'
            - consecutive_failures: 连续失败次数
        """
        try:
            with self.db.engine.connect() as conn:
                # 查询 Agent 信息
                agent_row = conn.execute(text("""
                    SELECT id, last_heartbeat, current_tasks, status, health_status,
                           consecutive_offline_count, max_offline_before_deactivate,
                           last_status_change
                    FROM agents
                    WHERE id = :agent_id
                """), {"agent_id": agent_id}).fetchone()
                
                if not agent_row:
                    return ('offline', 0)
                
                last_heartbeat = agent_row.last_heartbeat
                current_tasks = agent_row.current_tasks or 0
                current_status = agent_row.status or 'online'
                health_status = agent_row.health_status or 'online'
                consecutive_offline_count = agent_row.consecutive_offline_count or 0
                max_offline = agent_row.max_offline_before_deactivate or 3
                last_status_change = agent_row.last_status_change
                
                # 决策逻辑
                now = datetime.now()
                
                # 如果没有心跳记录
                if not last_heartbeat:
                    new_state = 'offline'
                    new_consecutive = consecutive_offline_count + 1
                else:
                    # 计算心跳时间差（秒）
                    if isinstance(last_heartbeat, str):
                        last_hb_time = datetime.fromisoformat(last_heartbeat)
                    else:
                        last_hb_time = last_heartbeat
                    
                    time_diff = (now - last_hb_time).total_seconds()
                    
                    # 状态决策
                    if time_diff >= HEARTBEAT_OFFLINE_THRESHOLD:
                        # 离线：无心跳超过阈值
                        new_state = 'offline'
                        new_consecutive = consecutive_offline_count + 1
                    elif current_tasks > 0:
                        # 有任务且心跳正常 → busy
                        new_state = 'busy'
                        new_consecutive = 0  # 有任务说明连通性正常
                    else:
                        # 无任务且心跳正常 → online
                        new_state = 'online'
                        new_consecutive = 0
                
                # 检查是否需要标记为 offline（连续失败/离线）
                if new_consecutive >= max_offline:
                    new_state = 'offline'
                
                return (new_state, new_consecutive)
                
        except Exception as e:
            logger.error(f"[HeartbeatDecision] Errordeciding state for {agent_id}: {e}")
            return ('offline', 0)
    
    def update_state(self, agent_id: str) -> dict:
        """
        更新 Agent 状态
        
        Args:
            agent_id: Agent ID
            
        Returns:
            更新后的状态信息
        """
        try:
            with self.db.engine.connect() as conn:
                # 决策新状态
                new_state, new_consecutive = self.decide_state(agent_id)
                
                # 更新数据库
                conn.execute(text("""
                    UPDATE agents
                    SET status = :status,
                        health_status = :status,
                        consecutive_offline_count = :consecutive,
                        last_status_change = :now,
                        updated_at = :now
                    WHERE id = :agent_id
                """), {
                    "agent_id": agent_id,
                    "status": new_state,
                    "consecutive": new_consecutive,
                    "now": datetime.now()
                })
                
                conn.commit()
                
                # 返回更新后的状态信息
                return {
                    "agent_id": agent_id,
                    "new_state": new_state,
                    "consecutive_offline_count": new_consecutive,
                    "updated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"[HeartbeatDecision] Error updating state for {agent_id}: {e}")
            return {
                "agent_id": agent_id,
                "error": str(e)
            }
    
    def on_heartbeat_failure(self, agent_id: str) -> dict:
        """
        处理心跳失败（ Agent 未按预期上报心跳）
        
        增加连续失败计数，检查是否需要标记为 offline
        
        Args:
            agent_id: Agent ID
            
        Returns:
            更新后的状态信息
        """
        try:
            with self.db.engine.connect() as conn:
                # 查询当前失败次数
                agent_row = conn.execute(text("""
                    SELECT consecutive_offline_count, max_offline_before_deactivate, status
                    FROM agents
                    WHERE id = :agent_id
                """), {"agent_id": agent_id}).fetchone()
                
                if not agent_row:
                    return {"error": "Agent not found"}
                
                current_failures = agent_row.consecutive_offline_count or 0
                max_failures = agent_row.max_offline_before_deactivate or 3
                current_status = agent_row.status or 'online'
                
                # 增加失败计数
                new_failures = current_failures + 1
                
                # 决策状态
                if new_failures >= max_failures:
                    new_state = 'offline'
                    # 重置失败计数（下次从 0 开始）
                    new_failures = 0
                else:
                    # 继续维持当前状态
                    new_state = current_status
                
                # 更新数据库
                conn.execute(text("""
                    UPDATE agents
                    SET status = :status,
                        health_status = :status,
                        consecutive_offline_count = :consecutive,
                        last_status_change = :now,
                        updated_at = :now
                    WHERE id = :agent_id
                """), {
                    "agent_id": agent_id,
                    "status": new_state,
                    "consecutive": new_failures,
                    "now": datetime.now()
                })
                
                conn.commit()
                
                return {
                    "agent_id": agent_id,
                    "old_state": current_status,
                    "new_state": new_state,
                    "failure_count": new_failures,
                    "max_failures": max_failures,
                    "updated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"[HeartbeatDecision] Error handling heartbeat failure for {agent_id}: {e}")
            return {
                "agent_id": agent_id,
                "error": str(e)
            }
    
    def on_heartbeat_success(self, agent_id: str) -> dict:
        """
        处理心跳成功（Agent 正常上报心跳）
        
        重置连续失败计数，根据任务数决定 online 或 busy
        
        Args:
            agent_id: Agent ID
            
        Returns:
            更新后的状态信息
        """
        try:
            with self.db.engine.connect() as conn:
                # 查询当前任务数
                agent_row = conn.execute(text("""
                    SELECT current_tasks, status, consecutive_offline_count
                    FROM agents
                    WHERE id = :agent_id
                """), {"agent_id": agent_id}).fetchone()
                
                if not agent_row:
                    return {"error": "Agent not found"}
                
                current_tasks = agent_row.current_tasks or 0
                current_status = agent_row.status or 'online'
                current_failures = agent_row.consecutive_offline_count or 0
                
                # 重置失败计数
                new_failures = 0
                
                # 决策状态
                if current_tasks > 0:
                    new_state = 'busy'
                else:
                    new_state = 'online'
                
                # 如果状态发生变化，更新时间戳
                status_changed = new_state != current_status
                
                # 更新数据库
                update_params = {
                    "agent_id": agent_id,
                    "status": new_state,
                    "consecutive": new_failures,
                    "now": datetime.now()
                }
                
                if status_changed:
                    update_params["last_status_change"] = datetime.now()
                    update_params["health_status"] = new_state
                    
                    conn.execute(text("""
                        UPDATE agents
                        SET status = :status,
                            health_status = :health_status,
                            consecutive_offline_count = :consecutive,
                            last_status_change = :last_status_change,
                            updated_at = :now
                        WHERE id = :agent_id
                    """), update_params)
                else:
                    conn.execute(text("""
                        UPDATE agents
                        SET status = :status,
                            consecutive_offline_count = :consecutive,
                            updated_at = :now
                        WHERE id = :agent_id
                    """), update_params)
                
                conn.commit()
                
                return {
                    "agent_id": agent_id,
                    "old_state": current_status if status_changed else None,
                    "new_state": new_state,
                    "current_tasks": current_tasks,
                    "failure_count_reset": current_failures,
                    "status_changed": status_changed,
                    "updated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"[HeartbeatDecision] Error handling heartbeat success for {agent_id}: {e}")
            return {
                "agent_id": agent_id,
                "error": str(e)
            }
    
    def scan_all_agents(self) -> dict:
        """
        扫描所有 Agent，更新状态
        
        Returns:
            统计信息
        """
        try:
            with self.db.engine.connect() as conn:
                # 查询所有 Agent
                agents = conn.execute(text("""
                    SELECT id, last_heartbeat, current_tasks, status,
                           consecutive_offline_count, max_offline_before_deactivate
                    FROM agents
                """)).fetchall()
                
                updates = []
                online_count = 0
                busy_count = 0
                offline_count = 0
                
                for agent in agents:
                    agent_id = agent.id
                    last_heartbeat = agent.last_heartbeat
                    current_tasks = agent.current_tasks or 0
                    current_status = agent.status or 'online'
                    consecutive = agent.consecutive_offline_count or 0
                    max_offline = agent.max_offline_before_deactivate or 3
                    
                    # 决策状态
                    now = datetime.now()
                    
                    if not last_heartbeat:
                        new_state = 'offline'
                        new_consecutive = consecutive + 1
                    else:
                        if isinstance(last_heartbeat, str):
                            last_hb_time = datetime.fromisoformat(last_heartbeat)
                        else:
                            last_hb_time = last_heartbeat
                        
                        time_diff = (now - last_hb_time).total_seconds()
                        
                        if time_diff >= HEARTBEAT_OFFLINE_THRESHOLD:
                            new_state = 'offline'
                            new_consecutive = consecutive + 1
                        elif current_tasks > 0:
                            new_state = 'busy'
                            new_consecutive = 0
                        else:
                            new_state = 'online'
                            new_consecutive = 0
                    
                    # 检查是否达到离线阈值
                    if new_consecutive >= max_offline:
                        new_state = 'offline'
                        new_consecutive = 0  # 重置
                    
                    # 更新计数
                    if new_state == 'online':
                        online_count += 1
                    elif new_state == 'busy':
                        busy_count += 1
                    else:
                        offline_count += 1
                    
                    # 记录更新
                    updates.append({
                        "agent_id": agent_id,
                        "new_state": new_state,
                        "consecutive": new_consecutive
                    })
                
                # 批量更新
                for u in updates:
                    conn.execute(text("""
                        UPDATE agents
                        SET status = :status,
                            health_status = :status,
                            consecutive_offline_count = :consecutive,
                            updated_at = :now
                        WHERE id = :agent_id
                    """), {
                        "agent_id": u["agent_id"],
                        "status": u["new_state"],
                        "consecutive": u["consecutive"],
                        "now": datetime.now()
                    })
                
                conn.commit()
                
                return {
                    "total": len(agents),
                    "online": online_count,
                    "busy": busy_count,
                    "offline": offline_count,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"[HeartbeatDecision] Error scanning agents: {e}")
            return {"error": str(e)}

def get_heartbeat_decision(db_manager):
    """获取 HeartbeatDecision 实例"""
    return HeartbeatDecision(db_manager)
