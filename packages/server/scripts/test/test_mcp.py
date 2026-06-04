"""
MCP API 测试脚本
"""

import requests
import json

BASE_URL = "http://localhost:8090"

def test_list_mcp_servers():
    """测试列出 MCP Server"""
    resp = requests.get(f"{BASE_URL}/api/v1/mcp-servers")
    print("GET /api/v1/mcp-servers:", resp.status_code)
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))

def test_create_mcp_server():
    """测试创建 MCP Server"""
    data = {
        "name": "新闻查询",
        "description": "获取最新新闻和热点资讯",
        "transport": "http",
        "url": "http://news.mcp.example",
        "category": "资讯",
        "tools": [
            {
                "name": "get_news",
                "description": "获取指定类别的新闻",
                "parameters": '{"category": {"type": "string"}}',
                "return_type": "json"
            }
        ]
    }
    resp = requests.post(f"{BASE_URL}/api/v1/mcp-servers", json=data)
    print("POST /api/v1/mcp-servers:", resp.status_code)
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
    return resp.json().get("id")

def test_get_mcp_server(server_id: str):
    """测试获取 MCP Server 详情"""
    resp = requests.get(f"{BASE_URL}/api/v1/mcp-servers/{server_id}")
    print(f"GET /api/v1/mcp-servers/{server_id}:", resp.status_code)
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))

def test_get_mcp_tools(server_id: str):
    """测试获取 MCP Server 的工具"""
    resp = requests.get(f"{BASE_URL}/api/v1/mcp-servers/{server_id}/tools")
    print(f"GET /api/v1/mcp-servers/{server_id}/tools:", resp.status_code)
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))

def test_match_agent(agent_id: str, agent_description: str):
    """测试 Agent-MCP 匹配"""
    data = {"agent_id": agent_id, "agent_description": agent_description}
    resp = requests.post(f"{BASE_URL}/api/v1/agents/{agent_id}/match-mcp", json=data)
    print(f"POST /api/v1/agents/{agent_id}/match-mcp:", resp.status_code)
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    print("=== MCP API 测试 ===\n")
    
    # 1. 测试列出 MCP Server
    test_list_mcp_servers()
    print("\n")
    
    # 2. 测试创建 MCP Server
    server_id = test_create_mcp_server()
    if server_id:
        print("\n")
        
        # 3. 测试获取 MCP Server 详情
        test_get_mcp_server(server_id)
        print("\n")
        
        # 4. 测试获取工具列表
        test_get_mcp_tools(server_id)
        print("\n")
        
        # 5. 测试 Agent-MCP 匹配
        test_match_agent("test-agent", "我负责资讯收集和热点追踪")
    
    print("\n=== 测试完成 ===")
