"""
Token 服务 - 处理 Token 的生成、验证、刷新、撤销
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .models import Token, TokenType
from shared.database.session import get_database_manager


class TokenService:
    """
    Token 服务类
    提供 Token 的全生命周期管理
    """

    DEFAULT_EXPIRY_HOURS = 24

    def __init__(self, db_session: Session = None):
        self.db = db_session or get_database_manager().get_session()

    def generate_token(
        self,
        token_type: TokenType,
        entity_id: str,
        name: str = None,
        expiry_hours: int = DEFAULT_EXPIRY_HOURS
    ) -> Tuple[str, Token]:
        """
        生成新 Token

        Args:
            token_type: Token 类型 (user/agent)
            entity_id: 关联的实体 ID (user_id 或 agent_id)
            name: Token 名称（可选）
            expiry_hours: 有效期（小时）

        Returns:
            Tuple[str, Token]: (明文 Token, Token 对象)
        """
        # 生成随机 Token
        raw_token = secrets.token_urlsafe(48)
        
        # 计算哈希
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        # 计算过期时间
        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        # 创建 Token 记录
        token_record = Token(
            hash=token_hash,
            type=token_type,
            name=name or f"{token_type}_token",
            expires_at=expires_at,
        )
        
        # 设置关联的 entity_id
        if token_type == TokenType.USER:
            token_record.user_id = entity_id
        else:
            token_record.agent_id = entity_id

        try:
            self.db.add(token_record)
            self.db.commit()
            self.db.refresh(token_record)
            
            return raw_token, token_record
        except SQLAlchemyError as e:
            self.db.rollback()
            raise ValueError(f"Failed to create token: {str(e)}")

    def verify_token(self, token: str) -> Optional[Token]:
        """
        验证 Token

        Args:
            token: 明文 Token

        Returns:
            Token: Token 对象（如果有效）
            None: Token 无效或已过期
        """
        if not token:
            return None

        token_hash = hashlib.sha256(token.encode()).hexdigest()

        try:
            token_record = self.db.query(Token).filter(
                Token.hash == token_hash,
                Token.revoked == 0
            ).first()

            if not token_record:
                return None

            # 检查过期
            if token_record.expires_at < datetime.utcnow():
                return None

            return token_record
        except SQLAlchemyError:
            return None

    def refresh_token(self, refresh_token: str, expiry_hours: int = DEFAULT_EXPIRY_HOURS) -> Optional[str]:
        """
        刷新 Token

        Args:
            refresh_token: 当前有效的 Token
            expiry_hours: 新 Token 的有效期（小时）

        Returns:
            str: 新 Token（如果刷新成功）
            None: 刷新失败
        """
        token_record = self.verify_token(refresh_token)
        
        if not token_record:
            return None

        # 撤销旧 Token
        self.revoke_token(token_record.token_id)

        # 生成新 Token
        new_type = token_record.type
        new_entity_id = token_record.user_id or token_record.agent_id
        new_name = token_record.name

        new_token, _ = self.generate_token(
            token_type=new_type,
            entity_id=new_entity_id,
            name=new_name,
            expiry_hours=expiry_hours
        )

        return new_token

    def revoke_token(self, token_id: int) -> bool:
        """
        撤销 Token

        Args:
            token_id: Token ID

        Returns:
            bool: 是否成功撤销
        """
        try:
            token_record = self.db.query(Token).filter(
                Token.token_id == token_id
            ).first()

            if not token_record:
                return False

            token_record.revoked = 1
            self.db.commit()
            return True

        except SQLAlchemyError:
            self.db.rollback()
            return False

    def get_token_by_id(self, token_id: int) -> Optional[Token]:
        """
        根据 ID 获取 Token

        Args:
            token_id: Token ID

        Returns:
            Token: Token 对象
        """
        try:
            return self.db.query(Token).filter(
                Token.token_id == token_id
            ).first()
        except SQLAlchemyError:
            return None

    def generate_agent_token(self, agent_id: str, name: str = "agent_token") -> Tuple[str, Token]:
        """
        为 Agent 生成 Token

        Args:
            agent_id: Agent ID
            name: Token 名称

        Returns:
            Tuple[str, Token]: (明文 Token, Token 对象)
        """
        return self.generate_token(
            token_type=TokenType.AGENT,
            entity_id=agent_id,
            name=name
        )

    def generate_user_token(self, user_id: str, name: str = "user_token") -> Tuple[str, Token]:
        """
        为用户生成 Token

        Args:
            user_id: 用户 ID
            name: Token 名称

        Returns:
            Tuple[str, Token]: (明文 Token, Token 对象)
        """
        return self.generate_token(
            token_type=TokenType.USER,
            entity_id=user_id,
            name=name
        )
