"""
MCP Tools 与 Agent 匹配逻辑
从 mcp_logic.py 拆分
"""

from typing import List, Dict, Any
from sqlalchemy import text

from reins.common.database import get_db_manager
from models import MCPServer, MCPTool


class MCPToolsAndMatching:
    """MCP Tools 列表与 Agent-MCP 自动匹配"""

    def __init__(self, match_helpers):
        self._db = get_db_manager()
        self._helpers = match_helpers

    def list_mcp_tools(self, server_id: str):
        """列出 MCP Server 的工具"""
        from fastapi import HTTPException

        server = self._db.query(MCPServer).filter(MCPServer.id == server_id).first()
        
        if not server:
            raise HTTPException(status_code=404, detail="MCP Server not found")

        tools = []
        tool_rows = self._db.query(MCPTool).filter(
            MCPTool.server_id == server_id
        ).order_by(MCPTool.name).all()

        for tool in tool_rows:
            tools.append({
                "id": tool.id,
                "server_id": tool.server_id,
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "return_type": tool.return_type,
            })

        return {"server_id": server_id, "tools": tools, "total": len(tools)}

    def match_agent_to_mcp(self, agent_id: str, agent_description: str):
        """Agent-MCP 自动匹配"""
        servers = self._db.query(MCPServer).filter(
            MCPServer.status == 'active'
        ).order_by(MCPServer.created_at).all()

        matches = []

        for server in servers:
            server_id = server.id

            tools = []
            tool_rows = self._db.query(MCPTool).filter(
                MCPTool.server_id == server_id
            ).all()

            for tool in tool_rows:
                tools.append({
                    "id": tool.id,
                    "server_id": tool.server_id,
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                    "return_type": tool.return_type,
                })

            score, reasons = self._helpers._calculate_match_score(agent_description, server.to_dict(), tools)

            if score > 0:
                matches.append({
                    "server_id": server_id,
                    "server_name": server.name,
                    "score": score,
                    "match_reasons": reasons,
                })

        matches.sort(key=lambda x: x["score"], reverse=True)

        return {
            "agent_id": agent_id,
            "agent_description": agent_description,
            "matches": matches,
            "total": len(matches),
        }
