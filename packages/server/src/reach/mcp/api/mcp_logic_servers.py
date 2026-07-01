"""
MCP Server CRUD 操作
从 mcp_logic.py 拆分
"""

from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from sqlalchemy.orm import Session
from models import MCPServer, MCPTool
from reins.common.database import get_db_session

class MCPServerCRUD:
    """MCP Server 增删改查"""

    def __init__(self):
        pass

    def _generate_uuid(self) -> str:
        return str(uuid.uuid4())

    def list_mcp_servers(self, category: Optional[str] = None, status: Optional[str] = None):
        """列出 MCP Server"""
        db = get_db_session()
        try:
            query = db.query(MCPServer)
            if category:
                query = query.filter(MCPServer.category == category)
            if status:
                query = query.filter(MCPServer.status == status)
            query = query.order_by(MCPServer.sort_order.asc(), MCPServer.created_at.desc())

            servers = query.all()
            results = []
            for s in servers:
                results.append({
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "transport": s.transport,
                    "url": s.url,
                    "icon": s.icon,
                    "category": s.category,
                    "sort_order": s.sort_order or 999,
                    "auth_type": s.auth_type,
                    "api_key": s.api_key,
                    "rate_limit": s.rate_limit,
                    "ssl_verify": s.ssl_verify,
                    "status": s.status,
                    "created_at": s.created_at,
                    "updated_at": s.updated_at,
                })
            return {"servers": results, "total": len(results)}
        finally:
            db.close()

    def get_mcp_server(self, server_id: str):
        """获取 MCP Server 详情"""
        from fastapi import HTTPException

        db = get_db_session()
        try:
            server = db.query(MCPServer).filter(MCPServer.id == server_id).first()
            if not server:
                raise HTTPException(status_code=404, detail="MCP Server not found")
            return {
                "id": server.id,
                "name": server.name,
                "description": server.description,
                "transport": server.transport,
                "url": server.url,
                "icon": server.icon,
                "category": server.category,
                "auth_type": server.auth_type,
                "api_key": server.api_key,
                "rate_limit": server.rate_limit,
                "ssl_verify": server.ssl_verify,
                "status": server.status,
                "created_at": server.created_at,
                "updated_at": server.updated_at,
            }
        finally:
            db.close()

    def create_mcp_server(self, server_data):
        """创建 MCP Server"""
        if hasattr(server_data, 'model_dump'):
            server_data = server_data.model_dump()

        server_id = self._generate_uuid()
        now = datetime.now()

        db = get_db_session()
        try:
            new_server = MCPServer(
                id=server_id,
                name=server_data.get("name"),
                description=server_data.get("description"),
                transport=server_data.get("transport", "sse"),
                url=server_data.get("url"),
                icon=server_data.get("icon"),
                category=server_data.get("category", "general"),
                sort_order=server_data.get("sort_order", 999),
                auth_type=server_data.get("auth_type", "none"),
                api_key=server_data.get("api_key"),
                rate_limit=server_data.get("rate_limit", 0),
                ssl_verify=server_data.get("ssl_verify", True),
                status="active",
                created_at=now,
                updated_at=now,
            )
            db.add(new_server)

            for tool in server_data.get("tools", []):
                tool_id = self._generate_uuid()
                if hasattr(tool, 'model_dump'):
                    tool = tool.model_dump()
                new_tool = MCPTool(
                    id=tool_id,
                    server_id=server_id,
                    name=tool.get("name"),
                    description=tool.get("description"),
                    parameters=tool.get("parameters", "{}"),
                    return_type=tool.get("return_type", "json"),
                )
                db.add(new_tool)

            db.commit()
            return {"id": server_id, "message": "MCP Server created successfully"}
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def update_mcp_server(self, server_id: str, server_data):
        """更新 MCP Server"""
        from fastapi import HTTPException

        if hasattr(server_data, 'model_dump'):
            server_data = server_data.model_dump(exclude_unset=True)
        else:
            server_data = {k: v for k, v in server_data.items() if v is not None}

        db = get_db_session()
        try:
            server = db.query(MCPServer).filter(MCPServer.id == server_id).first()
            if not server:
                raise HTTPException(status_code=404, detail="MCP Server not found")

            for field in ["name", "description", "transport", "url", "icon", "category",
                          "sort_order", "auth_type", "api_key", "rate_limit", "ssl_verify", "status"]:
                if field in server_data:
                    setattr(server, field, server_data[field])

            server.updated_at = datetime.now().isoformat()
            db.commit()
            return {"id": server_id, "message": "MCP Server updated successfully"}
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_mcp_server(self, server_id: str):
        """删除 MCP Server"""
        from fastapi import HTTPException

        db = get_db_session()
        try:
            server = db.query(MCPServer).filter(MCPServer.id == server_id).first()
            if not server:
                raise HTTPException(status_code=404, detail="MCP Server not found")

            # Delete associated tools
            db.query(MCPTool).filter(MCPTool.server_id == server_id).delete()
            db.delete(server)
            db.commit()
            return {"id": server_id, "message": "MCP Server deleted successfully"}
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
