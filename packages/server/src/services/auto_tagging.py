"""
自动能力标签标注 + 权重衰减

信号采集：Agent 完成任务后，自动增加其任务所用标签的权重
权重衰减：定期计算，长时间未观察到的标签权重递减
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.agent import Agent, AgentTagWeight
from reins.database import get_db_manager

# 权重衰减配置（天数）
EXPIRY_DAYS = {
    "technical": 30,      # 技术栈30天未用 → 权重降至0
    "professional": 60,   # 专业能力60天
    "business": 90,       # 业务领域90天
    "management": None,   # 管理能力不会过期
}

WEIGHT_INCREMENT = 0.1    # 每次观察到 +0.1
WEIGHT_DECAY = 0.05       # 每次tick未观察到 -0.05
MAX_WEIGHT = 1.0
MIN_WEIGHT = 0.0

def observe_task_completion(agent_id: str, task_capability_tags: dict):
    """
    任务完成信号：增加对应标签的权重

    Args:
        agent_id: 完成任务的 Agent ID
        task_capability_tags: 任务的 capability_tags (四维dict)
    """
    if not task_capability_tags:
        return

    db_manager = get_db_manager()
    engine = db_manager.engine
    with engine.begin() as conn:
        session = Session(bind=conn)
        try:
            now = datetime.utcnow()

            for dim in ["business", "professional", "technical", "management"]:
                tags = task_capability_tags.get(dim, [])
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except Exception:
                        tags = []

                for tag in tags:
                    if not tag:
                        continue

                    # 查询现有权重
                    existing = session.query(AgentTagWeight).filter(
                        AgentTagWeight.agent_id == agent_id,
                        AgentTagWeight.tag == tag
                    ).first()

                    if existing:
                        existing.weight = min(MAX_WEIGHT, existing.weight + WEIGHT_INCREMENT)
                        existing.last_observed = now
                    else:
                        new_weight = AgentTagWeight(
                            agent_id=agent_id,
                            tag=tag,
                            weight=0.3,  # 首次观察从0.3开始
                            last_observed=now,
                        )
                        session.add(new_weight)

            session.commit()
            logger.info(f"[AutoTag] Updated weights for agent {agent_id} from task completion")
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

def decay_weights() -> Dict[str, int]:
    """
    权重衰减：对长时间未观察到的标签降低权重

    Returns:
        {"decayed_count": int, "removed_count": int}
    """
    db_manager = get_db_manager()
    engine = db_manager.engine
    decayed = 0
    removed = 0

    with engine.begin() as conn:
        session = Session(bind=conn)
        try:
            # 获取所有权重记录
            rows = session.query(AgentTagWeight).all()

            now = datetime.utcnow()

            for row in rows:
                agent_id = row.agent_id
                tag = row.tag
                weight = row.weight
                last_observed = row.last_observed

                # 推断标签维度（通过 agent 的 capability_tags）
                agent_obj = session.query(Agent).filter(Agent.id == agent_id).first()
                if not agent_obj or not agent_obj.capability_tags:
                    continue

                try:
                    agent_tags = json.loads(agent_obj.capability_tags) if isinstance(agent_obj.capability_tags, str) else agent_obj.capability_tags
                except Exception:
                    continue

                # 找到标签所属维度
                dim = None
                for d in ["business", "professional", "technical", "management"]:
                    dim_tags = agent_tags.get(d, [])
                    if isinstance(dim_tags, str):
                        try:
                            dim_tags = json.loads(dim_tags)
                        except Exception:
                            dim_tags = []
                    if tag in dim_tags:
                        dim = d
                        break

                if dim is None:
                    continue  # 标签不属于任何维度，跳过

                expiry = EXPIRY_DAYS.get(dim)
                if expiry is None:
                    continue  # management 不会过期

                if last_observed:
                    days_since = (now - last_observed).total_seconds() / 86400
                    if days_since > expiry:
                        # 过期，删除该权重记录
                        session.delete(row)
                        removed += 1
                    elif days_since > expiry * 0.5:
                        # 接近过期，降低权重
                        row.weight = max(MIN_WEIGHT, weight - WEIGHT_DECAY)
                        decayed += 1

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return {"decayed_count": decayed, "removed_count": removed}
