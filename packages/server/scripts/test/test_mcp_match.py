# -*- coding: utf-8 -*-
"""
MCP API 测试脚本 - 验证匹配功能
"""

import requests
import json

BASE_URL = "http://localhost:8090"

def test_matching():
    """测试 Agent-MCP 匹配"""
    
    # 1. 创建天气 MCP Server
    weather_data = {
        "name": "天气服务",
        "description": "获取实时天气和天气预报",
        "transport": "sse",
        "url": "http://weather.mcp.example",
        "category": "数据",
        "tools": [
            {
                "name": "get_weather",
                "description": "获取指定城市的天气",
                "parameters": '{"city": {"type": "string"}}',
                "return_type": "json"
            },
            {
                "name": "get_forecast",
                "description": "获取天气预报信息",
                "parameters": '{"city": {"type": "string"}, "days": {"type": "integer"}}',
                "return_type": "json"
            }
        ]
    }
    
    print("=== 创建天气 MCP Server ===")
    resp = requests.post(f"{BASE_URL}/api/v1/mcp-servers", json=weather_data)
    print(f"Status: {resp.status_code}")
    weather_id = resp.json().get("id")
    print(f"ID: {weather_id}")
    print()
    
    # 2. 创建新闻 MCP Server
    news_data = {
        "name": "新闻服务",
        "description": "获取最新新闻和热点资讯",
        "transport": "http",
        "url": "http://news.mcp.example",
        "category": "资讯",
        "tools": [
            {
                "name": "get_news",
                "description": "获取新闻列表",
                "parameters": '{"category": {"type": "string"}}',
                "return_type": "json"
            }
        ]
    }
    
    print("=== 创建新闻 MCP Server ===")
    resp = requests.post(f"{BASE_URL}/api/v1/mcp-servers", json=news_data)
    print(f"Status: {resp.status_code}")
    news_id = resp.json().get("id")
    print(f"ID: {news_id}")
    print()
    
    # 3. 测试匹配 - 查找天气相关 Agent
    print("=== 测试匹配：Agent 负责天气和预报 ===")
    match_data = {
        "agent_id": "weather-agent",
        "agent_description": "我负责天气和预报"
    }
    resp = requests.post(f"{BASE_URL}/api/v1/agents/weather-agent/match-mcp", json=match_data)
    print(f"Status: {resp.status_code}")
    result = resp.json()
    print(f"Agent: {result.get('agent_id')}")
    print(f"Description: {result.get('agent_description')}")
    print(f"Matches: {result.get('total')}")
    for m in result.get('matches', []):
        print(f"  - {m['server_name']}: score={m['score']}, reasons={m['match_reasons']}")
    print()
    
    # 4. 测试匹配 - 查找资讯相关 Agent
    print("=== 测试匹配：Agent 负责新闻资讯 ===")
    match_data = {
        "agent_id": "news-agent", 
        "agent_description": "我负责新闻资讯"
    }
    resp = requests.post(f"{BASE_URL}/api/v1/agents/news-agent/match-mcp", json=match_data)
    print(f"Status: {resp.status_code}")
    result = resp.json()
    print(f"Matches: {result.get('total')}")
    for m in result.get('matches', []):
        print(f"  - {m['server_name']}: score={m['score']}, reasons={m['match_reasons']}")
    print()
    
    # 5. 列出所有 Server
    print("=== 列出所有 MCP Server ===")
    resp = requests.get(f"{BASE_URL}/api/v1/mcp-servers")
    print(f"Status: {resp.status_code}")
    servers = resp.json().get('servers', [])
    print(f"Total: {len(servers)}")
    for s in servers:
        print(f"  - {s['name']}: {s['description']}")

if __name__ == "__main__":
    test_matching()
