"""
调试关键词匹配逻辑
"""

def keyword_matching(desc: str, text: str) -> list:
    """关键词匹配"""
    if not desc or not text:
        return []
    
    keywords = [k.strip() for k in desc.replace('，', ' ').replace('、', ' ').split() if k.strip()]
    matched = []
    
    for kw in keywords:
        if kw.lower() in text.lower():
            matched.append(kw)
    
    return matched

# 测试
desc = "资讯收集和热点追踪"
server_name = "新闻查询"
server_desc = "获取最新新闻和热点资讯"
tool_name = "get_news"
tool_desc = "获取指定类别的新闻"

print("描述:", desc)
print("Server 名称:", server_name)
print("Server 描述:", server_desc)
print("Tool 名称:", tool_name)
print("Tool 描述:", tool_desc)
print()

print("关键词匹配 Server 名称:")
matched_names = keyword_matching(desc, server_name)
print(f"  {matched_names}")

print("关键词匹配 Server 描述:")
matched_desc = keyword_matching(desc, server_desc)
print(f"  {matched_desc}")

print("关键词匹配 Tool 名称:")
matched_tools = keyword_matching(desc, tool_name)
print(f"  {matched_tools}")

print("关键词匹配 Tool 描述:")
matched_tool_desc = keyword_matching(desc, tool_desc)
print(f"  {matched_tool_desc}")
