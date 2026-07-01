"""
Grever Reins - MCP Server API 路由

提供 MCP Server CRUD 和 Agent-MCP 自动匹配功能
Sprint 37: 麻子 - 后端实现

此文件为 facade，仅负责路由注册和请求转发。
业务逻辑已拆分至 mcp_logic.py
"""

import uuid
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import text

from reins.common.database import get_db_manager

router = APIRouter(prefix="/api/v1", tags=["MCP"])

# 延迟导入 logic 模块
_logic = None

def _get_logic():
    global _logic
    if _logic is None:
        from reach.mcp.api.mcp_logic import MCPServerLogic
        _logic = MCPServerLogic()
    return _logic

# ========= Pydantic Models =========

class ToolCreate(BaseModel):
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    parameters: str = Field(default="{}", description="参数定义 (JSON)")
    return_type: str = Field(default="json", description="返回类型")

class MCPServerCreate(BaseModel):
    name: str = Field(..., description="MCP Server 名称")
    description: Optional[str] = Field(None, description="描述")
    transport: str = Field(default="sse", description="传输协议 (sse/http)")
    url: str = Field(..., description="服务地址")
    icon: Optional[str] = Field(None, description="图标 URL")
    category: str = Field(default="general", description="分类")
    sort_order: int = Field(default=999, description="排序顺序（越小越靠前）")
    auth_type: str = Field(default="none", description="认证方式 (none/api_key/bearer/basic)")
    api_key: Optional[str] = Field(None, description="API 密钥")
    rate_limit: int = Field(default=0, description="每分钟请求限制（0表示不限制）")
    ssl_verify: bool = Field(default=True, description="是否验证 SSL 证书")
    tools: List[ToolCreate] = Field(default_factory=list, description="工具列表")

class MCPServerUpdate(BaseModel):
    name: Optional[str] = Field(None, description="MCP Server 名称")
    description: Optional[str] = Field(None, description="描述")
    transport: Optional[str] = Field(None, description="传输协议")
    url: Optional[str] = Field(None, description="服务地址")
    icon: Optional[str] = Field(None, description="图标 URL")
    category: Optional[str] = Field(None, description="分类")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    auth_type: Optional[str] = Field(None, description="认证方式 (none/api_key/bearer/basic)")
    api_key: Optional[str] = Field(None, description="API 密钥")
    rate_limit: Optional[int] = Field(None, description="每分钟请求限制（0表示不限制）")
    ssl_verify: Optional[bool] = Field(None, description="是否验证 SSL 证书")
    status: Optional[str] = Field(None, description="状态 (active/inactive)")

class AgentMatchRequest(BaseModel):
    agent_description: str = Field(default="", description="Agent 职责描述")

class MatchResult(BaseModel):
    server_id: str
    server_name: str
    score: int
    match_reasons: List[str]

class AgentMatchResponse(BaseModel):
    agent_id: str
    agent_description: str
    matches: List[MatchResult]

# ========= API Endpoints =========

@router.get("/mcp-servers")
def list_mcp_servers(
    category: Optional[str] = Query(None, description="分类过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
):
    """列出 MCP Server（支持过滤）"""
    return _get_logic().list_mcp_servers(category, status)

@router.get("/mcp-servers/{server_id}")
def get_mcp_server(server_id: str):
    """获取 MCP Server 详情"""
    return _get_logic().get_mcp_server(server_id)

@router.post("/mcp-servers")
def create_mcp_server(server_data: MCPServerCreate = Body(...)):
    """创建 MCP Server"""
    return _get_logic().create_mcp_server(server_data)

@router.put("/mcp-servers/{server_id}")
def update_mcp_server(server_id: str, server_data: MCPServerUpdate = Body(...)):
    """更新 MCP Server"""
    return _get_logic().update_mcp_server(server_id, server_data)

@router.delete("/mcp-servers/{server_id}")
def delete_mcp_server(server_id: str):
    """删除 MCP Server"""
    return _get_logic().delete_mcp_server(server_id)

@router.get("/mcp-servers/{server_id}/tools")
def list_mcp_tools(server_id: str):
    """列出 MCP Server 的工具"""
    return _get_logic().list_mcp_tools(server_id)

@router.post("/agents/{agent_id}/match-mcp")
def match_agent_to_mcp(
    agent_id: str,
    request_data: AgentMatchRequest = Body(...)
):
    """Agent-MCP 自动匹配"""
    return _get_logic().match_agent_to_mcp(agent_id, request_data.agent_description)

@router.get("/mcp")
def mcp_docs():
    """MCP API 文档（简单页面）"""
    return """
    <html>
    <head><title>MCP Server API</title></head>
    <body>
        <h1>MCP Server API</h1>
        <ul>
            <li><a href="/api/v1/mcp-servers">GET /api/v1/mcp-servers</a> - 列表</li>
            <li><a href="/api/v1/mcp-servers/{id}">GET /api/v1/mcp-servers/{id}</a> - 详情</li>
            <li><a href="/api/v1/mcp-servers">POST /api/v1/mcp-servers</a> - 创建</li>
            <li><a href="/api/v1/mcp-servers/{id}">PUT /api/v1/mcp-servers/{id}</a> - 更新</li>
            <li><a href="/api/v1/mcp-servers/{id}">DELETE /api/v1/mcp-servers/{id}</a> - 删除</li>
            <li><a href="/api/v1/mcp-servers/{id}/tools">GET /api/v1/mcp-servers/{id}/tools</a> - 工具列表</li>
            <li><a href="/api/v1/agents/{agent_id}/match-mcp">POST /api/v1/agents/{agent_id}/match-mcp</a> - 匹配</li>
        </ul>
    </body>
    </html>
    """