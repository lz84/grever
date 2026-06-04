"""
调试关键词匹配逻辑
"""

def keyword_matching(desc: str, text: str) -> list:
    """关键词匹配"""
    if not desc or not text:
        return []
    
    # 对于中文，尝试按常见词性分词
    import re
    
    # 先按空格、逗号、顿号等分割
    raw_keywords = [k.strip() for k in desc.replace('，', ' ').replace('、', ' ').replace('和', ' ').replace('与', ' ').replace('或', ' ').split() if k.strip()]
    
    # 合并单字（中文通常需要至少2个字才匹配）
    keywords = []
    i = 0
    while i < len(raw_keywords):
        kw = raw_keywords[i]
        # 如果是单字，尝试与下一个字合并
        if len(kw) == 1 and i + 1 < len(raw_keywords) and len(raw_keywords[i+1]) == 1:
            combined = kw + raw_keywords[i+1]
            if combined not in keywords:
                keywords.append(combined)
            i += 2
        else:
            if kw not in keywords:
                keywords.append(kw)
            i += 1
    
    matched = []
    
    for kw in keywords:
        if len(kw) >= 2 and kw.lower() in text.lower():
            matched.append(kw)
    
    return keywords, matched

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

print("关键词匹配 Server 描述:")
keys, matched = keyword_matching(desc, server_desc)
print(f"  分词结果: {keys}")
print(f"  匹配结果: {matched}")
