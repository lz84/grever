"""
Nexus Agent SDK - 智能体无缝注册到 Reins

P9-03: Agent SDK 适配 - 现有 Agent 无缝注册到 Reins

提供:
- AgentRegistrationConfig: 注册配置
- AgentSDK: Agent SDK 客户端（注册、心跳、发现、注销）

使用示例:
    from reach.common.agent_sdk import AgentSDK, AgentRegistrationConfig
    
    # 1. 配置
    config = AgentRegistrationConfig(
        server_url="http://localhost:8090",
        agent_id="my-agent-001",
        agent_name="My Agent",
        capabilities=["rescue", "search"],
    )
    
    # 2. 创建 SDK
    sdk = AgentSDK(config)
    
    # 3. 注册到 Reins
    result = sdk.register()
    logger.info(f"Token: {sdk.token}")
    
    # 4. 发送心跳
    sdk.heartbeat(status={"load": 30, "current_tasks": 2})
    
    # 5. 发现其他 Agent
    agents = sdk.discover()
    
    # 6. 注销
    sdk.unregister(reason="任务完成")
"""

from loguru import logger
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

import requests

# ============================================================================
# Configuration
# ============================================================================

@dataclass
class AgentRegistrationConfig:
    """
    Agent 注册配置
    
    Args:
        server_url: Reins Server 地址
        agent_id: Agent 唯一标识
        agent_name: Agent 显示名称
        capabilities: Agent 能力标签列表
        max_load: 最大并发任务数（默认 5）
        trigger_mode: 触发模式 sse/polling/callback（默认 sse）
        poll_interval_seconds: 轮询间隔秒数（默认 10）
        metadata: 附加元数据
    """
    server_url: str
    agent_id: str
    agent_name: str
    capabilities: List[str]
    max_load: int = 5
    trigger_mode: str = "sse"
    poll_interval_seconds: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为 API 请求体"""
        return {
            "agent_id": self.agent_id,
            "name": self.agent_name,
            "capabilities": self.capabilities,
            "max_load": self.max_load,
            "trigger_mode": self.trigger_mode,
            "poll_interval_seconds": self.poll_interval_seconds,
            "metadata": self.metadata,
        }

# ============================================================================
# Agent SDK Client
# ============================================================================

class AgentSDK:
    """
    Nexus Agent SDK 客户端
    
    让现有 Agent（OpenClaw、Paperclip 等）无缝注册到 Reins Server。
    
    功能:
    - register(): 注册到 Reins，获取认证 Token
    - heartbeat(): 发送心跳保持在线
    - discover(): 发现其他可用 Agent
    - unregister(): 注销 Agent
    - get_heartbeat_logs(): 查询心跳历史
    
    线程安全: 是（所有操作通过 HTTP 请求）
    """
    
    def __init__(self, config: AgentRegistrationConfig):
        """
        初始化 Agent SDK
        
        Args:
            config: 注册配置
        """
        self.config = config
        self._token: Optional[str] = None
        self._is_registered = False
        
        # Normalize server_url (remove trailing slash)
        self._base_url = config.server_url.rstrip("/")
        
        logger.info(
            f"[AgentSDK] Initialized: {config.agent_name} "
            f"({config.agent_id}) -> {self._base_url}"
        )
    
    @property
    def token(self) -> Optional[str]:
        """获取当前认证 Token"""
        return self._token
    
    @property
    def is_registered(self) -> bool:
        """是否已注册"""
        return self._is_registered
    
    def _headers(self) -> Dict[str, str]:
        """获取请求头（含认证）"""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers
    
    # ---- Core Operations ----
    
    def register(self) -> Optional[Dict[str, Any]]:
        """
        注册 Agent 到 Reins Server
        
        注册成功后:
        - 自动生成认证 Token（通过响应头 X-Agent-Token 返回）
        - Agent 状态变为 online
        - 开始接收任务分配
        
        Returns:
            Agent 信息字典，失败返回 None
        """
        url = f"{self._base_url}/api/v1/agents"
        payload = self.config.to_dict()
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 提取认证 Token（从响应头）
            token = response.headers.get("X-Agent-Token")
            if token:
                self._token = token
                logger.info(f"[AgentSDK] Registered: {self.config.agent_name}, token: {token[:16]}...")
            else:
                logger.warning(f"[AgentSDK] Registered but no token in response headers")
            
            self._is_registered = True
            return data
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[AgentSDK] Connection failed: {self._base_url} - {e}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"[AgentSDK] Timeout: {self._base_url} - {e}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"[AgentSDK] HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"[AgentSDK] Registration failed: {e}")
            return None
    
    def heartbeat(self, status: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        发送心跳到 Reins Server
        
        Args:
            status: 可选的状态信息
                - load: 当前负载百分比 (0-100)
                - current_tasks: 当前任务数
                - latency_ms: 请求延迟（毫秒）
        
        Returns:
            心跳响应，失败返回 None
        """
        if not self._is_registered:
            logger.warning("[AgentSDK] Not registered, call register() first")
            return None
        
        url = f"{self._base_url}/api/v1/agents/{self.config.agent_id}/heartbeat"
        
        try:
            response = requests.post(
                url,
                json=status or {},
                headers=self._headers(),
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[AgentSDK] Heartbeat failed: {e}")
            return None
    
    def unregister(self, reason: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        从 Reins Server 注销 Agent
        
        Args:
            reason: 注销原因
        
        Returns:
            注销响应，失败返回 None
        """
        url = f"{self._base_url}/api/v1/agents/{self.config.agent_id}"
        
        try:
            params = {}
            if reason:
                params["reason"] = reason
            
            response = requests.delete(
                url,
                params=params,
                headers=self._headers(),
                timeout=10,
            )
            response.raise_for_status()
            
            self._is_registered = False
            logger.info(f"[AgentSDK] Unregistered: {self.config.agent_name}")
            return response.json()
        except Exception as e:
            logger.error(f"[AgentSDK] Unregister failed: {e}")
            return None
    
    # ---- Discovery ----
    
    def discover(
        self,
        capabilities: Optional[List[str]] = None,
        status: Optional[str] = None,
        max_load: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        发现其他可用 Agent
        
        Args:
            capabilities: 按能力过滤
            status: 按状态过滤 (online/offline/error)
            max_load: 最大负载过滤
        
        Returns:
            Agent 列表
        """
        url = f"{self._base_url}/api/v1/discover"
        
        params = {}
        if capabilities:
            params["capabilities"] = capabilities
        if status:
            params["status"] = status
        if max_load is not None:
            params["max_load"] = max_load
        
        try:
            response = requests.get(
                url,
                params=params,
                headers=self._headers(),
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[AgentSDK] Discover failed: {e}")
            return []
    
    def find_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        查找特定 Agent
        
        Args:
            agent_id: Agent ID
        
        Returns:
            Agent 信息，不存在返回 None
        """
        url = f"{self._base_url}/api/v1/discover/{agent_id}"
        
        try:
            response = requests.get(
                url,
                headers=self._headers(),
                timeout=10,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[AgentSDK] Find agent failed: {e}")
            return None
    
    # ---- Heartbeat Logs ----
    
    def get_heartbeat_logs(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        获取 Agent 心跳日志
        
        Args:
            limit: 返回条数（默认 20，最大 100）
            offset: 偏移量
        
        Returns:
            心跳日志响应
        """
        url = f"{self._base_url}/api/v1/agents/{self.config.agent_id}/heartbeat_logs"
        
        try:
            response = requests.get(
                url,
                params={"limit": limit, "offset": offset},
                headers=self._headers(),
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[AgentSDK] Get heartbeat logs failed: {e}")
            return {"logs": [], "total": 0}
    
    # ---- Trigger Mode ----
    
    def set_trigger_mode(self, mode: str) -> Optional[Dict[str, Any]]:
        """
        设置触发模式
        
        Args:
            mode: sse / polling / callback
        
        Returns:
            更新响应
        """
        url = f"{self._base_url}/api/v1/agents/{self.config.agent_id}/trigger_mode"
        
        try:
            response = requests.patch(
                url,
                json={"trigger_mode": mode},
                headers=self._headers(),
                timeout=10,
            )
            response.raise_for_status()
            self.config.trigger_mode = mode
            return response.json()
        except Exception as e:
            logger.error(f"[AgentSDK] Set trigger mode failed: {e}")
            return None

# ============================================================================
# Convenience Functions
# ============================================================================

def create_agent(
    server_url: str,
    agent_id: str,
    agent_name: str,
    capabilities: List[str],
    **kwargs,
) -> AgentSDK:
    """
    便捷函数：创建 Agent SDK 实例
    
    Args:
        server_url: Reins Server 地址
        agent_id: Agent ID
        agent_name: Agent 名称
        capabilities: 能力列表
        **kwargs: 其他配置参数（max_load, trigger_mode 等）
    
    Returns:
        AgentSDK 实例
    """
    config = AgentRegistrationConfig(
        server_url=server_url,
        agent_id=agent_id,
        agent_name=agent_name,
        capabilities=capabilities,
        **kwargs,
    )
    return AgentSDK(config)

def register_and_get_token(
    server_url: str,
    agent_id: str,
    agent_name: str,
    capabilities: List[str],
    **kwargs,
) -> Optional[str]:
    """
    便捷函数：注册 Agent 并返回 Token
    
    Args:
        server_url: Reins Server 地址
        agent_id: Agent ID
        agent_name: Agent 名称
        capabilities: 能力列表
        **kwargs: 其他配置参数
    
    Returns:
        认证 Token，失败返回 None
    """
    sdk = create_agent(server_url, agent_id, agent_name, capabilities, **kwargs)
    result = sdk.register()
    if result:
        return sdk.token
    return None
