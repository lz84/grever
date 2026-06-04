"""
MCP Tools 与 Agent 匹配逻辑
从 mcp_logic.py 拆分
"""

from typing import List, Dict, Any
from sqlalchemy import text

from reins.common.database import get_db_manager

class MCPToolsAndMatching:
    """MCP Tools 列表与 Agent-MCP 自动匹配"""

    def __init__(self, match_helpers):
        self._db = get_db_manager()
        self._helpers = match_helpers

    def list_mcp_tools(self, server_id: str):
        """列出 MCP Server 的工具"""
        from fastapi import HTTPException

        with self._db.engine.connect() as conn:
            row = conn.execute(
                text("SELECT id FROM mcp_servers WHERE id = :id"),
                {"id": server_id}
            ).fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="MCP Server not found")

            tools = []
            rows = conn.execute(
                text("SELECT * FROM mcp_tools WHERE server_id = :server_id ORDER BY name"),
                {"server_id": server_id}
            ).fetchall()

            for row in rows:
                d = dict(row._mapping)
                tools.append({
                    "id": d.get("id"),
                    "server_id": d.get("server_id"),
                    "name": d.get("name"),
                    "description": d.get("description"),
                    "parameters": d.get("parameters"),
                    "return_type": d.get("return_type"),
                })

            return {"server_id": server_id, "tools": tools, "total": len(tools)}

    def match_agent_to_mcp(self, agent_id: str, agent_description: str):
        """Agent-MCP 自动匹配"""
        with self._db.engine.connect() as conn:
            servers = conn.execute(
                text("SELECT * FROM mcp_servers WHERE status = 'active' ORDER BY created_at")
            ).fetchall()

            matches = []

            for server_row in servers:
                server = dict(server_row._mapping)
                server_id = server.get("id")

                tools = []
                tool_rows = conn.execute(
                    text("SELECT * FROM mcp_tools WHERE server_id = :server_id"),
                    {"server_id": server_id}
                ).fetchall()

                for tool_row in tool_rows:
                    tools.append(dict(tool_row._mapping))

                score, reasons = self._helpers._calculate_match_score(agent_description, server, tools)

                if score > 0:
                    matches.append({
                        "server_id": server_id,
                        "server_name": server.get("name", ""),
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
