"""
测试 Token 服务
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.auth.models import Token, TokenType, Base
from shared.auth.service import TokenService


@pytest.fixture
def db_session():
    """创建测试数据库和 session"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_generate_token(db_session):
    """测试生成 Token"""
    service = TokenService(db_session)
    
    raw_token, token_record = service.generate_token(
        token_type=TokenType.USER,
        entity_id="test-user-123",
        name="test_token",
    )
    
    assert raw_token is not None
    assert len(raw_token) > 0
    assert token_record.token_id is not None
    assert token_record.type == TokenType.USER
    assert token_record.user_id == "test-user-123"
    assert token_record.name == "test_token"


def test_generate_agent_token(db_session):
    """测试生成 Agent Token"""
    service = TokenService(db_session)
    
    raw_token, token_record = service.generate_agent_token(
        agent_id="agent-001",
        name="agent_auth_token",
    )
    
    assert token_record.type == TokenType.AGENT
    assert token_record.agent_id == "agent-001"


def test_verify_valid_token(db_session):
    """测试验证有效 Token"""
    service = TokenService(db_session)
    
    # 生成 Token
    raw_token, _ = service.generate_token(
        token_type=TokenType.USER,
        entity_id="user-001",
    )
    
    # 验证 Token
    token_record = service.verify_token(raw_token)
    
    assert token_record is not None
    assert token_record.user_id == "user-001"


def test_verify_invalid_token(db_session):
    """测试验证无效 Token"""
    service = TokenService(db_session)
    
    token_record = service.verify_token("invalid_token_12345")
    assert token_record is None


def test_verify_expired_token(db_session):
    """测试验证过期 Token"""
    service = TokenService(db_session)
    
    # 生成已过期的 Token
    expired_token, _ = service.generate_token(
        token_type=TokenType.USER,
        entity_id="user-001",
        expiry_hours=-1,  # 已过期
    )
    
    # 验证过期 Token
    token_record = service.verify_token(expired_token)
    assert token_record is None


def test_revoke_token(db_session):
    """测试撤销 Token"""
    service = TokenService(db_session)
    
    # 生成 Token
    raw_token, token_record = service.generate_token(
        token_type=TokenType.USER,
        entity_id="user-001",
    )
    
    # 撤销 Token
    success = service.revoke_token(token_record.token_id)
    assert success is True
    
    # 验证已撤销的 Token
    token_record_after = service.verify_token(raw_token)
    assert token_record_after is None


def test_refresh_token(db_session):
    """测试刷新 Token"""
    service = TokenService(db_session)
    
    # 生成原始 Token
    original_token, original_record = service.generate_token(
        token_type=TokenType.USER,
        entity_id="user-001",
        name="refresh_test_token",
    )
    
    # 刷新 Token
    new_token = service.refresh_token(original_token)
    
    assert new_token is not None
    assert new_token != original_token
    
    # 原始 Token 应该已撤销
    original_verified = service.verify_token(original_token)
    assert original_verified is None
    
    # 新 Token 应该有效
    new_verified = service.verify_token(new_token)
    assert new_verified is not None
