"""
测试 Token 模型
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.auth.models import Token, TokenType, Base


@pytest.fixture
def db_session():
    """创建测试数据库和 session"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_token_creation(db_session):
    """测试 Token 创建"""
    token = Token(
        hash="test_hash_value",
        type=TokenType.USER,
        name="test_token",
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    
    db_session.add(token)
    db_session.commit()
    
    assert token.token_id is not None
    assert token.hash == "test_hash_value"
    assert token.type == TokenType.USER


def test_token_enum():
    """测试 Token 类型枚举"""
    assert TokenType.USER == "user"
    assert TokenType.AGENT == "agent"


def test_token_revoked_flag(db_session):
    """测试 Token 撤销标志"""
    token = Token(
        hash="test_revoked",
        type=TokenType.AGENT,
        name="revoked_token",
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    
    db_session.add(token)
    db_session.commit()
    
    assert token.revoked == 0
    
    token.revoked = 1
    db_session.commit()
    
    assert token.revoked == 1
