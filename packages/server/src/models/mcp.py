"""MCP Server and Tool models - ORM + Pydantic schemas"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from typing import Optional, List, Dict, Any
from .base import Base
from .schema_factory import auto_schema


def _generate_mcp_server_id():
    return f"mcp-{uuid.uuid4().hex[:12]}"


class MCPServer(Base):
    """
    MCP Server 表
    
    存储 MCP (Model Context Protocol) 服务器配置。
    """
    __tablename__ = 'mcp_servers'

    id = Column(String(36), primary_key=True, default=_generate_mcp_server_id)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(Text, nullable=False)  # MCP server URL
    api_key = Column(Text, nullable=True)  # Optional API key
    status = Column(String(50), default='active')  # active/inactive
    sort_order = Column(Integer, nullable=False, default=999)  # 排序字段，越小越靠前
    transport = Column(String(50), nullable=True, default='sse')  # 传输方式
    icon = Column(Text, nullable=True)  # 图标
    category = Column(String(50), nullable=True, default='general')  # 分类
    auth_type = Column(String(50), nullable=True, default='none')  # 认证类型
    rate_limit = Column(Integer, nullable=True, default=0)  # 速率限制
    ssl_verify = Column(Integer, nullable=True, default=1)  # SSL 验证
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def _serialize_dt(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value if value else None
        return value.isoformat()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'url': self.url,
            'status': self.status,
            'sort_order': self.sort_order,
            'transport': self.transport,
            'icon': self.icon,
            'category': self.category,
            'auth_type': self.auth_type,
            'api_key': self.api_key,
            'rate_limit': self.rate_limit,
            'ssl_verify': self.ssl_verify,
            'created_at': self._serialize_dt(self.created_at),
            'updated_at': self._serialize_dt(self.updated_at),
        }

    def __repr__(self):
        return f"<MCPServer(id={self.id}, name='{self.name}', status='{self.status}')>"


def _generate_mcp_tool_id():
    return f"mcp-tool-{uuid.uuid4().hex[:12]}"


class MCPTool(Base):
    """
    MCP Tool 表
    
    存储 MCP Server 提供的工具定义。
    """
    __tablename__ = 'mcp_tools'

    id = Column(String(36), primary_key=True, default=_generate_mcp_tool_id)
    server_id = Column(String(36), ForeignKey('mcp_servers.id'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    parameters = Column(Text, nullable=True)  # JSON: 参数定义
    return_type = Column(String(100), nullable=True)  # 返回类型
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    server = relationship('MCPServer', back_populates='tools')

    def _serialize_dt(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value if value else None
        return value.isoformat()

    def _parse_json(self, value):
        """解析 JSON 字符串"""
        import json
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value

    def to_dict(self):
        return {
            'id': self.id,
            'server_id': self.server_id,
            'name': self.name,
            'description': self.description,
            'parameters': self._parse_json(self.parameters),
            'return_type': self.return_type,
            'created_at': self._serialize_dt(self.created_at),
            'updated_at': self._serialize_dt(self.updated_at),
        }

    def __repr__(self):
        return f"<MCPTool(id={self.id}, name='{self.name}')>"


# 关系初始化（必须在类定义之后）
MCPServer.tools = relationship('MCPTool', back_populates='server', cascade='all, delete-orphan')


# Auto-generated Pydantic schemas
MCPServerCreate, MCPServerUpdate, MCPServerResponse = auto_schema(
    MCPServer,
)

MCPToolCreate, MCPToolUpdate, MCPToolResponse = auto_schema(
    MCPTool,
)
