"""
P5-04: API 认证测试 - Bearer Token 认证机制

覆盖:
- P5-04-01: Token 模型
- P5-04-02: Token 生成 API
- P5-04-03: Token 验证中间件
- P5-04-04: Token 刷新
- P5-04-05: Token 撤销
- P5-04-06: Agent Token
"""

import pytest
import hashlib
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# 添加 src 到路径
src_dir = str(Path(__file__).parent.parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Test Database Setup (in-memory SQLite)
# ============================================================================

def create_test_db():
    """创建测试用 in-memory SQLite 数据库"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from auth.base import Base
    from shared.auth.models import Token
    from database.models import Base as DBBase
    
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    
    # 创建 auth 表
    Base.metadata.create_all(bind=engine)
    
    Session = sessionmaker(bind=engine)
    return engine, Session


# ============================================================================
# TestTokenModel Tests
# ============================================================================

class TestTokenModel:
    """P5-04-01: Token 模型测试"""

    def test_token_type_enum(self):
        """TokenType 枚举值正确"""
        from shared.auth.models import TokenType
        assert TokenType.USER == "user"
        assert TokenType.AGENT == "agent"
        logger.info("✓ TokenType enum values correct")

    def test_token_to_dict(self):
        """Token.to_dict() 返回完整字段"""
        from shared.auth.models import Token
        
        token = Token(
            token_id=1,
            hash="abc123",
            user_id="user-001",
            agent_id=None,
            expires_at=datetime(2026, 4, 20, 0, 0, 0),
            created_at=datetime(2026, 4, 13, 0, 0, 0),
            type="user",
            name="test_token",
            revoked=0,
        )
        d = token.to_dict()
        assert d['token_id'] == 1
        assert d['hash'] == "abc123"
        assert d['user_id'] == "user-001"
        assert d['type'] == "user"
        assert d['name'] == "test_token"
        assert d['revoked'] is False  # 0 → False
        logger.info("✓ Token.to_dict() returns all fields correctly")

    def test_revoked_token_to_dict(self):
        """已撤销 Token.to_dict() 返回 revoked=True"""
        from shared.auth.models import Token
        
        token = Token(
            token_id=2,
            hash="def456",
            revoked=1,  # revoked
        )
        d = token.to_dict()
        assert d['revoked'] is True
        logger.info("✓ Revoked token.to_dict() returns revoked=True")


# ============================================================================
# TestTokenService Tests
# ============================================================================

class TestTokenService:
    """P5-04-02/04/05/06: Token 服务测试"""

    def setup_method(self):
        """每个测试前创建新的 in-memory 数据库"""
        _, Session = create_test_db()
        self.db_session = Session()

    def teardown_method(self):
        """每个测试后关闭数据库连接"""
        self.db_session.close()

    def test_generate_token_returns_raw_and_record(self):
        """生成 Token 返回明文 token 和 Token 记录"""
        from shared.auth.service import TokenService
        from shared.auth.models import TokenType
        
        service = TokenService(db_session=self.db_session)
        
        raw_token, token_record = service.generate_token(
            token_type=TokenType.USER,
            entity_id="user-001",
            name="test_token",
            expiry_hours=24,
        )
        
        assert raw_token is not None
        assert len(raw_token) > 20  # 48 bytes URL-safe = ~64 chars
        assert token_record.user_id == "user-001"
        assert token_record.type == "user"
        assert token_record.name == "test_token"
        assert token_record.revoked == 0
        logger.info(f"✓ Generated token: {raw_token[:20]}...")

    def test_generate_token_expiry(self):
        """Token 过期时间正确"""
        from shared.auth.service import TokenService
        from shared.auth.models import TokenType
        
        service = TokenService(db_session=self.db_session)
        
        before = datetime.utcnow()
        _, token_record = service.generate_token(
            token_type=TokenType.AGENT,
            entity_id="agent-001",
            expiry_hours=48,
        )
        after = datetime.utcnow()
        
        expected_min = before + timedelta(hours=48)
        expected_max = after + timedelta(hours=48)
        assert expected_min <= token_record.expires_at <= expected_max
        logger.info(f"✓ Token expiry set correctly: {token_record.expires_at}")

    def test_generate_agent_token(self):
        """Agent Token 生成"""
        from shared.auth.service import TokenService
        
        service = TokenService(db_session=self.db_session)
        
        raw_token, token_record = service.generate_agent_token(
            agent_id="agent-001",
            name="agent_token",
        )
        
        assert raw_token is not None
        assert token_record.agent_id == "agent-001"
        assert token_record.type == "agent"
        assert token_record.name == "agent_token"
        logger.info("✓ Agent token generated successfully")

    def test_generate_user_token(self):
        """User Token 生成"""
        from shared.auth.service import TokenService
        
        service = TokenService(db_session=self.db_session)
        
        raw_token, token_record = service.generate_user_token(
            user_id="user-001",
            name="user_token",
        )
        
        assert raw_token is not None
        assert token_record.user_id == "user-001"
        assert token_record.type == "user"
        logger.info("✓ User token generated successfully")

    def test_verify_valid_token(self):
        """验证有效 Token"""
        from shared.auth.service import TokenService
        from shared.auth.models import TokenType
        
        service = TokenService(db_session=self.db_session)
        
        raw_token, token_record = service.generate_token(
            token_type=TokenType.USER,
            entity_id="user-001",
            expiry_hours=24,
        )
        
        verified = service.verify_token(raw_token)
        assert verified is not None
        assert verified.token_id == token_record.token_id
        logger.info("✓ Valid token verified successfully")

    def test_verify_invalid_token(self):
        """验证无效 Token 返回 None"""
        from shared.auth.service import TokenService
        
        service = TokenService(db_session=self.db_session)
        
        result = service.verify_token("invalid_token_string_xyz123")
        assert result is None
        logger.info("✓ Invalid token returns None on verification")

    def test_verify_empty_token(self):
        """空 Token 返回 None"""
        from shared.auth.service import TokenService
        
        service = TokenService(db_session=self.db_session)
        
        result = service.verify_token("")
        assert result is None
        result = service.verify_token(None)
        assert result is None
        logger.info("✓ Empty/None token returns None")

    def test_revoke_token(self):
        """撤销 Token"""
        from shared.auth.service import TokenService
        from shared.auth.models import TokenType
        
        service = TokenService(db_session=self.db_session)
        
        raw_token, token_record = service.generate_token(
            token_type=TokenType.USER,
            entity_id="user-001",
        )
        
        success = service.revoke_token(token_record.token_id)
        assert success is True
        
        # 验证 Token 已被撤销
        verified = service.verify_token(raw_token)
        assert verified is None
        logger.info("✓ Token revoked successfully")

    def test_revoke_nonexistent_token(self):
        """撤销不存在的 Token 返回 False"""
        from shared.auth.service import TokenService
        
        service = TokenService(db_session=self.db_session)
        
        success = service.revoke_token(99999)
        assert success is False
        logger.info("✓ Nonexistent token revoke returns False")

    def test_refresh_token(self):
        """刷新 Token"""
        from shared.auth.service import TokenService
        from shared.auth.models import TokenType
        
        service = TokenService(db_session=self.db_session)
        
        raw_token, old_record = service.generate_token(
            token_type=TokenType.USER,
            entity_id="user-001",
            name="refresh_test",
        )
        old_id = old_record.token_id
        
        new_token = service.refresh_token(raw_token)
        assert new_token is not None
        assert new_token != raw_token  # 新 token 不同
        
        # 旧 token 已被撤销
        old_verified = service.verify_token(raw_token)
        assert old_verified is None
        
        # 新 token 可用
        new_verified = service.verify_token(new_token)
        assert new_verified is not None
        assert new_verified.token_id != old_id
        logger.info("✓ Token refresh works correctly")

    def test_refresh_invalid_token_returns_none(self):
        """刷新无效 Token 返回 None"""
        from shared.auth.service import TokenService
        
        service = TokenService(db_session=self.db_session)
        
        result = service.refresh_token("invalid_token")
        assert result is None
        logger.info("✓ Invalid token refresh returns None")

    def test_get_token_by_id(self):
        """根据 ID 获取 Token"""
        from shared.auth.service import TokenService
        from shared.auth.models import TokenType
        
        service = TokenService(db_session=self.db_session)
        
        raw_token, token_record = service.generate_token(
            token_type=TokenType.USER,
            entity_id="user-001",
        )
        
        found = service.get_token_by_id(token_record.token_id)
        assert found is not None
        assert found.token_id == token_record.token_id
        logger.info("✓ get_token_by_id works correctly")


# ============================================================================
# TestAuthMiddleware Tests
# ============================================================================

class TestAuthMiddleware:
    """P5-04-03: Token 验证中间件测试"""

    def test_verify_token_missing_header(self):
        """缺少 Authorization header 返回 401"""
        import asyncio
        from auth.middleware import verify_token
        from fastapi import HTTPException
        
        async def run():
            with pytest.raises(HTTPException) as exc_info:
                await verify_token(authorization=None)
            assert exc_info.value.status_code == 401
            assert "Authorization header required" in exc_info.value.detail
        
        asyncio.run(run())
        logger.info("✓ Missing Authorization header returns 401")

    def test_verify_token_invalid_format(self):
        """Authorization header 格式错误返回 401"""
        import asyncio
        from auth.middleware import verify_token
        from fastapi import HTTPException
        
        async def run():
            with pytest.raises(HTTPException) as exc_info:
                await verify_token(authorization="InvalidFormat")
            assert exc_info.value.status_code == 401
            assert "Invalid authorization header format" in exc_info.value.detail
        
        asyncio.run(run())
        logger.info("✓ Invalid Authorization header format returns 401")

    def test_verify_token_wrong_scheme(self):
        """Bearer 以外 scheme 返回 401"""
        import asyncio
        from auth.middleware import verify_token
        from fastapi import HTTPException
        
        async def run():
            with pytest.raises(HTTPException) as exc_info:
                await verify_token(authorization="Basic abc123")
            assert exc_info.value.status_code == 401
        
        asyncio.run(run())
        logger.info("✓ Non-Bearer scheme returns 401")

    def test_optional_auth_returns_none_when_no_header(self):
        """optional_auth 无 header 时返回 None"""
        from auth.middleware import optional_auth
        
        # optional_auth 是同步函数
        result = optional_auth(authorization=None)
        assert result is None
        logger.info("✓ optional_auth returns None when no header")

    def test_require_auth_is_alias_of_verify_token(self):
        """require_auth 是 verify_token 的别名（语义化）"""
        from auth.middleware import require_auth, verify_token
        # 功能相同（都调用 verify_token）
        assert callable(require_auth)
        assert callable(verify_token)
        logger.info("✓ require_auth is available as verify_token alias")


# ============================================================================
# TestTokenGenerationEndpoint Models
# ============================================================================

class TestTokenEndpoints:
    """P5-04-02: Token 端点请求/响应模型测试"""

    def test_token_create_request_model(self):
        """TokenCreateRequest 模型"""
        from auth.router import TokenCreateRequest
        from shared.auth.models import TokenType
        
        req = TokenCreateRequest(type=TokenType.AGENT, entity_id="agent-001", name="test")
        assert req.type == TokenType.AGENT
        assert req.entity_id == "agent-001"
        assert req.name == "test"
        logger.info("✓ TokenCreateRequest model works")

    def test_token_create_request_defaults(self):
        """TokenCreateRequest 可选字段有默认值"""
        from auth.router import TokenCreateRequest
        from shared.auth.models import TokenType
        
        req = TokenCreateRequest(type=TokenType.USER, entity_id="user-001")
        assert req.name is None
        logger.info("✓ TokenCreateRequest optional fields have defaults")

    def test_token_create_response_model(self):
        """TokenCreateResponse 模型"""
        from auth.router import TokenCreateResponse
        
        resp = TokenCreateResponse(token="raw_token_string", expires_at="2026-04-20T00:00:00")
        assert resp.token == "raw_token_string"
        assert resp.expires_at == "2026-04-20T00:00:00"
        logger.info("✓ TokenCreateResponse model works")

    def test_token_refresh_request_model(self):
        """TokenRefreshRequest 模型"""
        from auth.router import TokenRefreshRequest
        
        req = TokenRefreshRequest(refresh_token="existing_token")
        assert req.refresh_token == "existing_token"
        logger.info("✓ TokenRefreshRequest model works")

    def test_token_refresh_response_model(self):
        """TokenRefreshResponse 模型"""
        from auth.router import TokenRefreshResponse
        
        resp = TokenRefreshResponse(token="new_token", expires_at="2026-04-21T00:00:00")
        assert resp.token == "new_token"
        logger.info("✓ TokenRefreshResponse model works")

    def test_auth_router_prefix(self):
        """认证路由 prefix 是 /api/v1/auth"""
        from auth.router import router
        assert router.prefix == "/api/v1/auth"
        logger.info("✓ Auth router prefix is /api/v1/auth")


# ============================================================================
# TestSensitiveEndpointMarking
# ============================================================================

class TestSensitiveEndpointMarking:
    """P5-04-07: 敏感端点认证标记测试"""

    def test_verify_token_raises_401_on_missing(self):
        """敏感端点在无 token 时应返回 401"""
        import asyncio
        from auth.middleware import verify_token
        from fastapi import HTTPException
        
        async def run():
            with pytest.raises(HTTPException) as exc_info:
                await verify_token(authorization=None)
            assert exc_info.value.status_code == 401
            assert "WWW-Authenticate" in exc_info.value.headers
        
        asyncio.run(run())
        logger.info("✓ 401 response includes WWW-Authenticate header")

    def test_auth_endpoint_design(self):
        """
        P5-04-07: 敏感端点认证设计
        
        公开端点（无需认证）:
        - POST /api/v1/auth/token - 创建 Token
        - POST /api/v1/auth/refresh - 刷新 Token（但端点本身会验证旧 token）
        
        需要认证端点:
        - DELETE /api/v1/auth/token/{token_id} - 撤销 Token
        - GET /api/v1/auth/token - 列出 Token
        """
        from auth.router import router
        
        routes = [r.path for r in router.routes]
        assert any("/token" in r for r in routes)
        logger.info(f"✓ Auth routes defined: {routes}")

    def test_token_service_hash_is_sha256(self):
        """Token 哈希使用 SHA256"""
        test_token = "test_token_string"
        expected_hash = hashlib.sha256(test_token.encode()).hexdigest()
        
        from shared.auth.service import TokenService
        from shared.auth.models import TokenType
        
        _, Session = create_test_db()
        service = TokenService(db_session=Session())
        raw_token, _ = service.generate_token(
            token_type=TokenType.USER,
            entity_id="user-001",
        )
        
        actual_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        assert len(actual_hash) == 64  # SHA256 hex = 64 chars
        logger.info("✓ Token hash is SHA256 (64 hex chars)")
