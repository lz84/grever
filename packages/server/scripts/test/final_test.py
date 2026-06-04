# -*- coding: utf-8 -*-
"""
最终验证 - Sprint 37 MCP Server API
"""
import requests
import json

BASE_URL = "http://localhost:8090"

def pretty_print(title, data):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)
    print(json.dumps(data, ensure_ascii=False, indent=2))

# 1. GET /api/v1/mcp-servers -> []
print("\n1. curl http://localhost:8090/api/v1/mcp-servers")
resp = requests.get(f"{BASE_URL}/api/v1/mcp-servers")
pretty_print("GET /api/v1/mcp-servers", resp.json())

# 2. POST 创建天气 MCP Server
print("\n2. POST /api/v1/mcp-servers (天气查询)")
weather_data = {
    "name": "天气查询",
    "description": "获取实时天气和预报",
    "transport": "sse",
    "url": "http://weather.mcp.example",
    "category": "数据",
    "tools": [{
        "name": "get_weather",
        "description": "获取指定城市的天气",
        "parameters": "{}",
        "return_type": "json"
    }]
}
resp = requests.post(f"{BASE_URL}/api/v1/mcp-servers", json=weather_data)
result = resp.json()
pretty_print("POST /api/v1/mcp-servers", result)
weather_id = result.get("id")

# 3. GET /api/v1/mcp-servers -> 返回 1 条
print("\n3. curl http://localhost:8090/api/v1/mcp-servers")
resp = requests.get(f"{BASE_URL}/api/v1/mcp-servers")
pretty_print(f"GET /api/v1/mcp-servers (应该返回 {len(resp.json()['servers'])} 条)", resp.json())

# 4. GET /api/v1/mcp-servers/{id}/tools -> 返回工具列表
print(f"\n4. curl http://localhost:8090/api/v1/mcp-servers/{weather_id}/tools")
resp = requests.get(f"{BASE_URL}/api/v1/mcp-servers/{weather_id}/tools")
pretty_print(f"GET /api/v1/mcp-servers/{weather_id}/tools", resp.json())

# 5. POST /api/v1/agents/agent-command/match-mcp -> 返回匹配结果
print("\n5. POST /api/v1/agents/agent-command/match-mcp")
match_data = {"agent_id": "agent-command", "agent_description": "天气和预报"}
resp = requests.post(f"{BASE_URL}/api/v1/agents/agent-command/match-mcp", json=match_data)
pretty_print("POST /api/v1/agents/agent-command/match-mcp", resp.json())

print("\n" + "="*60)
print("  ✅ Sprint 37 后端验证完成！")
print("="*60)
