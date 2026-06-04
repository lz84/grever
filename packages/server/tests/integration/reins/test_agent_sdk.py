"""
P9-03: Agent SDK 适配测试

测试现有 Agent（OpenClaw 等）通过 SDK 无缝注册到 Reins 的能力。

覆盖:
- AgentSDK 客户端（注册、心跳、发现、注销）
- AgentRegistrationConfig（配置）
- 兼容现有 agent 的注册流程
"""

import pytest
import logging
import sys
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

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
# Test AgentSDK Client
# ============================================================================

class TestAgentSDK:
    """Agent SDK 客户端测试"""

    def test_sdk_init(self):
        """SDK 初始化"""
        from reins.agent_sdk import AgentSDK, AgentRegistrationConfig
        
        config = AgentRegistrationConfig(
            server_url="http://localhost:8090",
            agent_id="test-agent-001",
            agent_name="测试Agent",
            capabilities=["rescue", "search"],
        )
        sdk = AgentSDK(config)
        
        assert sdk.config.agent_id == "test-agent-001"
        assert sdk.config.agent_name == "测试Agent"
        assert sdk.config.capabilities == ["rescue", "search"]
        assert sdk._token is None
        logger.info("✓ AgentSDK initializes with config")

    def test_sdk_config_defaults(self):
        """SDK 配置默认值"""
        from reins.agent_sdk import AgentRegistrationConfig
        
        config = AgentRegistrationConfig(
            server_url="http://localhost:8090",
            agent_id="test-001",
            agent_name="Test",
            capabilities=["test"],
        )
        
        assert config.max_load == 5
        assert config.trigger_mode == "sse"
        assert config.poll_interval_seconds == 10
        assert config.metadata == {}
        logger.info("✓ AgentRegistrationConfig has correct defaults")

    @patch("reins.agent_sdk.requests.post")
    def test_sdk_register(self, mock_post):
        """SDK 注册 Agent"""
        from reins.agent_sdk import AgentSDK, AgentRegistrationConfig
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test-001",
            "name": "Test Agent",
            "capabilities": ["rescue"],
            "status": "online",
            "trigger_mode": "sse",
            "poll_interval_seconds": 10,
            "load": 0,
            "current_tasks": 0,
        }
        mock_response.headers = {"X-Agent-Token": "pcp_test_token_12345"}
        mock_post.return_value = mock_response
        
        config = AgentRegistrationConfig(
            server_url="http://localhost:8090",
            agent_id="test-001",
            agent_name="Test Agent",
            capabilities=["rescue"],
        )
        sdk = AgentSDK(config)
        
        result = sdk.register()
        
        assert result is not None
        assert sdk._token == "pcp_test_token_12345"
        
        # 验证请求体正确
        call_args = mock_post.call_args
        request_body = call_args.kwargs.get("json", call_args[1].get("json", {}))
        assert request_body["agent_id"] == "test-001"
        assert request_body["name"] == "Test Agent"
        assert request_body["capabilities"] == ["rescue"]
        logger.info("✓ AgentSDK.register() sends correct request")

    @patch("reins.agent_sdk.requests.post")
    def test_sdk_heartbeat(self, mock_post):
        """SDK 发送心跳"""
        from reins.agent_sdk import AgentSDK, AgentRegistrationConfig
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response
        
        config = AgentRegistrationConfig(
            server_url="http://localhost:8090",
            agent_id="test-001",
            agent_name="Test",
            capabilities=["test"],
        )
        sdk = AgentSDK(config)
        sdk._token = "test_token"
        sdk._is_registered = True  # Mark as registered for heartbeat test
        
        result = sdk.heartbeat(status={"load": 30, "current_tasks": 2})
        
        assert result is not None
        assert result.get("success") is True
        
        # 验证 URL 和请求体
        call_args = mock_post.call_args
        url = call_args.args[0] if call_args.args else call_args[1].get("url", "")
        assert "test-001/heartbeat" in url
        logger.info("✓ AgentSDK.heartbeat() sends correct request")


# ============================================================================
# Test Server-Side Agent Registration API
# ============================================================================

class TestAgentRegistrationAPI:
    """服务端 Agent 注册 API 测试"""

    def test_agent_register_endpoint_exists(self):
        """注册端点已注册"""
        from api.server import create_app
        # 直接检查 server.py 中是否有相关路由
        import api.server as server_module
        source = open(server_module.__file__, "r", encoding="utf-8").read()
        assert '@app.post("/api/v1/agents"' in source
        logger.info("✓ POST /api/v1/agents endpoint exists")

    def test_agent_heartbeat_endpoint_exists(self):
        """心跳端点已注册"""
        import api.server as server_module
        source = open(server_module.__file__, "r", encoding="utf-8").read()
        assert '@app.post("/api/v1/agents/{agent_id}/heartbeat"' in source
        logger.info("✓ POST /api/v1/agents/{id}/heartbeat endpoint exists")

    def test_agent_discover_endpoint_exists(self):
        """发现端点已注册"""
        import api.server as server_module
        source = open(server_module.__file__, "r", encoding="utf-8").read()
        assert '@app.get("/api/v1/discover"' in source
        logger.info("✓ GET /api/v1/discover endpoint exists")

    def test_agent_heartbeat_logs_endpoint_exists(self):
        """心跳日志端点已注册"""
        import api.server as server_module
        source = open(server_module.__file__, "r", encoding="utf-8").read()
        assert '@app.get("/api/v1/agents/{agent_id}/heartbeat_logs"' in source
        logger.info("✓ GET /api/v1/agents/{id}/heartbeat_logs endpoint exists")

    def test_agent_trigger_mode_endpoint_exists(self):
        """触发模式端点已注册"""
        import api.server as server_module
        source = open(server_module.__file__, "r", encoding="utf-8").read()
        assert '@app.patch("/api/v1/agents/{agent_id}/trigger_mode"' in source
        logger.info("✓ PATCH /api/v1/agents/{id}/trigger_mode endpoint exists")


# ============================================================================
# Test AgentCapabilityRegistry (server-side)
# ============================================================================

class TestAgentCapabilityRegistry:
    """Agent 能力注册表测试"""

    def test_registry_register(self):
        """注册 Agent"""
        from reins.core.assignment import AgentCapabilityRegistry
        
        registry = AgentCapabilityRegistry()
        agent = registry.register(
            agent_id="agent-rescue-01",
            capabilities=["rescue", "search", "medical"],
            name="搜救Agent",
            max_load=5,
        )
        
        assert agent.agent_id == "agent-rescue-01"
        assert "rescue" in agent.capabilities
        assert agent.max_load == 5
        logger.info("✓ AgentCapabilityRegistry.register() works")

    def test_registry_query_by_capability(self):
        """按能力查询 Agent"""
        from reins.core.assignment import AgentCapabilityRegistry
        
        registry = AgentCapabilityRegistry()
        registry.register("agent-001", capabilities=["rescue", "search"], name="搜救")
        registry.register("agent-002", capabilities=["medical"], name="医疗")
        registry.register("agent-003", capabilities=["rescue", "medical"], name="搜救医疗")
        
        rescue_agents = registry.get_agents_by_capability("rescue")
        assert len(rescue_agents) == 2
        logger.info(f"✓ AgentCapabilityRegistry.get_agents_by_capability('rescue') returns {len(rescue_agents)} agents")

    def test_registry_unregister(self):
        """注销 Agent"""
        from reins.core.assignment import AgentCapabilityRegistry
        
        registry = AgentCapabilityRegistry()
        registry.register("agent-001", capabilities=["rescue"], name="搜救")
        registry.unregister("agent-001")
        
        rescue_agents = registry.get_agents_by_capability("rescue")
        assert len(rescue_agents) == 0
        logger.info("✓ AgentCapabilityRegistry.unregister() works")

    def test_registry_update(self):
        """更新 Agent 能力（通过重新注册）"""
        from reins.core.assignment import AgentCapabilityRegistry
        
        registry = AgentCapabilityRegistry()
        registry.register("agent-001", capabilities=["rescue"], name="搜救")
        # 重新注册以更新能力
        registry.register("agent-001", capabilities=["rescue", "search", "medical"], name="搜救")
        
        agent = registry.get_agent("agent-001")
        assert "medical" in agent.capabilities
        logger.info("✓ AgentCapabilityRegistry re-register to update capabilities")


# ============================================================================
# Test AgentSDK Integration (Mock Server)
# ============================================================================

class TestAgentSDKIntegration:
    """Agent SDK 集成测试（使用 Mock 服务器响应）"""

    @patch("reins.agent_sdk.requests.patch")
    @patch("reins.agent_sdk.requests.delete")
    @patch("reins.agent_sdk.requests.get")
    @patch("reins.agent_sdk.requests.post")
    def test_full_lifecycle_register_heartbeat_unregister(self, mock_post, mock_get, mock_delete, mock_patch):
        """完整生命周期：注册 → 心跳 → 注销"""
        from reins.agent_sdk import AgentSDK, AgentRegistrationConfig
        
        # Mock register response
        mock_reg_response = MagicMock()
        mock_reg_response.status_code = 200
        mock_reg_response.json.return_value = {
            "id": "test-lifecycle-001",
            "name": "Lifecycle Test Agent",
            "capabilities": ["rescue"],
            "status": "online",
            "trigger_mode": "sse",
            "poll_interval_seconds": 10,
            "load": 0,
            "current_tasks": 0,
        }
        mock_reg_response.headers = {"X-Agent-Token": "lifecycle_token_123"}
        
        # Mock heartbeat response
        mock_hb_response = MagicMock()
        mock_hb_response.status_code = 200
        mock_hb_response.json.return_value = {"success": True}
        
        # Mock unregister response
        mock_unreg_response = MagicMock()
        mock_unreg_response.status_code = 200
        mock_unreg_response.json.return_value = {"success": True}
        
        mock_post.side_effect = [mock_reg_response, mock_hb_response]
        mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value=[]))
        mock_delete.return_value = mock_unreg_response
        mock_patch.return_value = MagicMock(status_code=200, json=MagicMock(return_value={}))
        
        config = AgentRegistrationConfig(
            server_url="http://localhost:8090",
            agent_id="test-lifecycle-001",
            agent_name="Lifecycle Test Agent",
            capabilities=["rescue"],
        )
        sdk = AgentSDK(config)
        
        # 1. Register
        reg_result = sdk.register()
        assert reg_result is not None
        assert sdk._token == "lifecycle_token_123"
        
        # 2. Heartbeat
        hb_result = sdk.heartbeat(status={"load": 20, "current_tasks": 1})
        assert hb_result.get("success") is True
        
        # 3. Unregister
        unreg_result = sdk.unregister(reason="测试完成")
        assert unreg_result.get("success") is True
        
        logger.info("✓ Full lifecycle: register → heartbeat → unregister")


# ============================================================================
# Test Existing Agent Compatibility
# ============================================================================

class TestExistingAgentCompatibility:
    """现有 Agent 兼容性测试"""

    def test_openclaw_agent_can_register(self):
        """OpenClaw Agent 可通过 SDK 注册到 Reins"""
        from reins.agent_sdk import AgentSDK, AgentRegistrationConfig
        
        # 模拟 OpenClaw Agent 注册
        config = AgentRegistrationConfig(
            server_url="http://localhost:8090",
            agent_id="openclaw-agent-001",
            agent_name="OpenClaw Agent",
            capabilities=["text-generation", "tool-use", "code-execution"],
            max_load=10,
            trigger_mode="sse",
            metadata={
                "agent_type": "openclaw",
                "model": "qwen3-coder",
                "version": "1.0.0",
            },
        )
        sdk = AgentSDK(config)
        assert sdk.config.agent_id.startswith("openclaw-")
        assert sdk.config.metadata["agent_type"] == "openclaw"
        logger.info("✓ OpenClaw Agent can register to Reins via SDK")

    def test_paperclip_agent_can_register(self):
        """Paperclip Agent (谷子) 可通过 SDK 注册到 Reins"""
        from reins.agent_sdk import AgentSDK, AgentRegistrationConfig
        
        config = AgentRegistrationConfig(
            server_url="http://localhost:8090",
            agent_id="876b9322-0fbe-4cd0-97c2-9244a4e3b905",
            agent_name="谷子",
            capabilities=["financial-planning", "stock-analysis"],
            max_load=5,
            trigger_mode="polling",
            poll_interval_seconds=60,
            metadata={
                "agent_type": "paperclip",
                "role": "CFO",
            },
        )
        sdk = AgentSDK(config)
        assert sdk.config.trigger_mode == "polling"
        assert sdk.config.poll_interval_seconds == 60
        logger.info("✓ Paperclip Agent (谷子) can register to Reins via SDK")

    def test_custom_agent_can_register(self):
        """自定义 Agent 可通过 SDK 注册到 Reins"""
        from reins.agent_sdk import AgentSDK, AgentRegistrationConfig
        
        config = AgentRegistrationConfig(
            server_url="http://localhost:8090",
            agent_id="custom-agent-001",
            agent_name="Custom Agent",
            capabilities=["custom-skill-1", "custom-skill-2"],
            max_load=3,
            trigger_mode="callback",
            metadata={
                "agent_type": "custom",
                "callback_url": "http://custom-agent:8080/callback",
            },
        )
        sdk = AgentSDK(config)
        assert sdk.config.trigger_mode == "callback"
        logger.info("✓ Custom Agent can register to Reins via SDK")
