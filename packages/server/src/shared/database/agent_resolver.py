"""
Agent Resolver — DB 驱动的 Agent ID/code 转换

取代硬编码 AGENT_UUID_TO_CODE 字典和 DEFAULT_VERIFIER 常量。
所有 Agent UUID ↔ OpenClaw agent code 转换统一走这里。
"""

from typing import Optional
from sqlalchemy.orm import Session
from loguru import logger

from models.agent import Agent
from models.system_config import SystemConfig


def get_agent_code(session: Session, agent_id: str) -> Optional[str]:
    """
    Agent UUID → OpenClaw agent code.
    替代硬编码 AGENT_UUID_TO_CODE 字典。
    """
    agent = session.query(Agent).filter(Agent.id == agent_id).first()
    if agent and agent.agent_code:
        return agent.agent_code
    logger.warning(f"[agent_resolver] agent {agent_id} has no agent_code")
    return None


def get_agent_id(session: Session, agent_code: str) -> Optional[str]:
    """
    OpenClaw agent code → Agent UUID.
    替代 DEFAULT_VERIFIER 硬编码。
    """
    agent = session.query(Agent).filter(Agent.agent_code == agent_code).first()
    if agent:
        return agent.id
    logger.warning(f"[agent_resolver] no agent found for code '{agent_code}'")
    return None


def get_default_verifier_id(session: Session) -> Optional[str]:
    """
    从 system_config 读取默认验证器 agent code，再查 UUID。
    替代硬编码 DEFAULT_VERIFIER = "3745f1f0-..."。
    """
    config = session.query(SystemConfig).filter(
        SystemConfig.key == 'default-verifier-agent'
    ).first()
    if not config:
        logger.warning("[agent_resolver] no default-verifier-agent in system_config, falling back to kouzi")
        return get_agent_id(session, 'kouzi')
    return get_agent_id(session, config.value)
