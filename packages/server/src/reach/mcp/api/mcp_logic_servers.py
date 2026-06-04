"""
MCP Server CRUD 操作
从 mcp_logic.py 拆分
"""

from typing import Optional, Dict, Any
from datetime import datetime
import uuid
from sqlalchemy import text

from reins.common.database import get_db_manager

class MCPServerCRUD:
    """MCP Server 增删改查"""

    def __init__(self):
        self._db = get_db_manager()

    def _generate_uuid(self) -> str:
        return str(uuid.uuid4())

    def list_mcp_servers(self, category: Optional[str] = None, status: Optional[str] = None):
        """列出 MCP Server"""
        with self._db.engine.connect() as conn:
            query = "SELECT * FROM mcp_servers WHERE 1=1"
            params: Dict[str, Any] = {}

            if category:
                query += " AND category = :category"
                params["category"] = category

            if status:
                query += " AND status = :status"
                params["status"] = status

            query += " ORDER BY sort_order ASC, created_at DESC"

            rows = conn.execute(text(query), params).fetchall()

            servers = []
            for row in rows:
                d = dict(row._mapping)
                servers.append({
                    "id": d.get("id"),
                    "name": d.get("name"),
                    "description": d.get("description"),
                    "transport": d.get("transport"),
                    "url": d.get("url"),
                    "icon": d.get("icon"),
                    "category": d.get("category"),
                    "sort_order": d.get("sort_order", 999),
                    "auth_type": d.get("auth_type"),
                    "api_key": d.get("api_key"),
                    "rate_limit": d.get("rate_limit"),
                    "ssl_verify": d.get("ssl_verify"),
                    "status": d.get("status"),
                    "created_at": d.get("created_at"),
                    "updated_at": d.get("updated_at"),
                })

            return {"servers": servers, "total": len(servers)}

    def get_mcp_server(self, server_id: str):
        """获取 MCP Server 详情"""
        from fastapi import HTTPException

        with self._db.engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM mcp_servers WHERE id = :id"),
                {"id": server_id}
            ).fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="MCP Server not found")

            d = dict(row._mapping)
            return {
                "id": d.get("id"),
                "name": d.get("name"),
                "description": d.get("description"),
                "transport": d.get("transport"),
                "url": d.get("url"),
                "icon": d.get("icon"),
                "category": d.get("category"),
                "auth_type": d.get("auth_type"),
                "api_key": d.get("api_key"),
                "rate_limit": d.get("rate_limit"),
                "ssl_verify": d.get("ssl_verify"),
                "status": d.get("status"),
                "created_at": d.get("created_at"),
                "updated_at": d.get("updated_at"),
            }

    def create_mcp_server(self, server_data):
        """创建 MCP Server"""
        if hasattr(server_data, 'model_dump'):
            server_data = server_data.model_dump()

        server_id = self._generate_uuid()

        with self._db.engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO mcp_servers 
                    (id, name, description, transport, url, icon, category, sort_order, auth_type, api_key, rate_limit, ssl_verify, status, created_at, updated_at)
                    VALUES (:id, :name, :description, :transport, :url, :icon, :category, :sort_order, :auth_type, :api_key, :rate_limit, :ssl_verify, :status, :created_at, :updated_at)
                """),
                {
                    "id": server_id,
                    "name": server_data.get("name"),
                    "description": server_data.get("description"),
                    "transport": server_data.get("transport", "sse"),
                    "url": server_data.get("url"),
                    "icon": server_data.get("icon"),
                    "category": server_data.get("category", "general"),
                    "sort_order": server_data.get("sort_order", 999),
                    "auth_type": server_data.get("auth_type", "none"),
                    "api_key": server_data.get("api_key"),
                    "rate_limit": server_data.get("rate_limit", 0),
                    "ssl_verify": server_data.get("ssl_verify", True),
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
            )

            for tool in server_data.get("tools", []):
                tool_id = self._generate_uuid()
                if hasattr(tool, 'model_dump'):
                    tool = tool.model_dump()
                conn.execute(
                    text("""
                        INSERT INTO mcp_tools 
                        (id, server_id, name, description, parameters, return_type)
                        VALUES (:id, :server_id, :name, :description, :parameters, :return_type)
                    """),
                    {
                        "id": tool_id,
                        "server_id": server_id,
                        "name": tool.get("name"),
                        "description": tool.get("description"),
                        "parameters": tool.get("parameters", "{}"),
                        "return_type": tool.get("return_type", "json"),
                    }
                )

        return {"id": server_id, "message": "MCP Server created successfully"}

    def update_mcp_server(self, server_id: str, server_data):
        """更新 MCP Server"""
        from fastapi import HTTPException

        if hasattr(server_data, 'model_dump'):
            server_data = server_data.model_dump(exclude_unset=True)
        else:
            server_data = {k: v for k, v in server_data.items() if v is not None}

        with self._db.engine.connect() as conn:
            row = conn.execute(
                text("SELECT id FROM mcp_servers WHERE id = :id"),
                {"id": server_id}
            ).fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="MCP Server not found")

        update_fields = {}
        for field in ["name", "description", "transport", "url", "icon", "category",
                      "sort_order", "auth_type", "api_key", "rate_limit", "ssl_verify", "status"]:
            if field in server_data:
                update_fields[field] = server_data[field]

        update_fields["updated_at"] = datetime.now().isoformat()

        if update_fields:
            with self._db.engine.begin() as conn:
                set_clauses = ", ".join([f"{k} = :{k}" for k in update_fields.keys()])
                conn.execute(
                    text(f"UPDATE mcp_servers SET {set_clauses} WHERE id = :id"),
                    {"id": server_id, **update_fields}
                )

        return {"id": server_id, "message": "MCP Server updated successfully"}

    def delete_mcp_server(self, server_id: str):
        """删除 MCP Server"""
        from fastapi import HTTPException

        with self._db.engine.begin() as conn:
            row = conn.execute(
                text("SELECT id FROM mcp_servers WHERE id = :id"),
                {"id": server_id}
            ).fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="MCP Server not found")

            conn.execute(
                text("DELETE FROM mcp_tools WHERE server_id = :server_id"),
                {"server_id": server_id}
            )

            conn.execute(
                text("DELETE FROM mcp_servers WHERE id = :id"),
                {"id": server_id}
            )

        return {"id": server_id, "message": "MCP Server deleted successfully"}
