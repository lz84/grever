"""
MCP Server API 业务逻辑 — Facade

子模块:
  - mcp_logic_helpers: 关键词匹配与评分
  - mcp_logic_servers: MCP Server CRUD
  - mcp_logic_tools: Tools 列表与 Agent 匹配
"""

from .mcp_logic_helpers import MCPMatchHelpers
from .mcp_logic_servers import MCPServerCRUD
from .mcp_logic_tools import MCPToolsAndMatching

class MCPServerLogic:
    """MCP Server 业务逻辑（组合模式）"""

    def __init__(self):
        self._helpers = MCPMatchHelpers()
        self._servers = MCPServerCRUD()
        self._tools = MCPToolsAndMatching(self._helpers)

    # --- 透传到 helpers ---
    def _keyword_matching(self, desc: str, text: str):
        return self._helpers._keyword_matching(desc, text)

    def _calculate_match_score(self, agent_description: str, server: dict, tools: list):
        return self._helpers._calculate_match_score(agent_description, server, tools)

    # --- 透传到 servers CRUD ---
    def list_mcp_servers(self, category=None, status=None):
        return self._servers.list_mcp_servers(category, status)

    def get_mcp_server(self, server_id: str):
        return self._servers.get_mcp_server(server_id)

    def create_mcp_server(self, server_data):
        return self._servers.create_mcp_server(server_data)

    def update_mcp_server(self, server_id: str, server_data):
        return self._servers.update_mcp_server(server_id, server_data)

    def delete_mcp_server(self, server_id: str):
        return self._servers.delete_mcp_server(server_id)

    # --- 透传到 tools & matching ---
    def list_mcp_tools(self, server_id: str):
        return self._tools.list_mcp_tools(server_id)

    def match_agent_to_mcp(self, agent_id: str, agent_description: str):
        return self._tools.match_agent_to_mcp(agent_id, agent_description)
