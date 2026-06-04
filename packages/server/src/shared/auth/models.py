"""
Token 数据模型
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.orm import relationship
from typing import Optional
from .base import Base


class TokenType(str, Enum):
    """Token 类型"""
    USER = "user"
    AGENT = "agent"


class Token(Base):
    """
    Token 模型 - 存储 API 认证 Token
    
    字段:
        token_id: Token ID
        hash: SHA256 哈希（实际存储的值）
        user_id: 关联的用户 ID (简化为字符串，不使用外键)
        agent_id: 关联的 Agent ID (简化为字符串，不使用外键)
        expires_at: 过期时间
        created_at: 创建时间
        type: Token 类型 (user/agent)
        name: Token 名称
        revoked: 是否已撤销
    """
    __tablename__ = 'tokens'

    token_id = Column(Integer, primary_key=True, autoincrement=True)
    hash = Column(String(256), nullable=False, unique=True, index=True)
    user_id = Column(String(200), nullable=True, index=True)
    agent_id = Column(String(200), nullable=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    type = Column(String(20), nullable=False, default='user')
    name = Column(String(100), nullable=True)
    revoked = Column(Integer, default=0)  # 0: active, 1: revoked

    # 索引
    __table_args__ = (
        Index('idx_tokens_user_id', 'user_id'),
        Index('idx_tokens_agent_id', 'agent_id'),
        Index('idx_tokens_type_expires', 'type', 'expires_at'),
        Index('idx_tokens_hash', 'hash'),
    )

    def to_dict(self) -> dict:
        return {
            'token_id': self.token_id,
            'hash': self.hash,
            'user_id': self.user_id,
            'agent_id': self.agent_id,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'type': self.type,
            'name': self.name,
            'revoked': self.revoked == 1,
        }

    def __repr__(self) -> str:
        return f"<Token(token_id={self.token_id}, type='{self.type}', name='{self.name}')>"
