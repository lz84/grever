"""
调试关键词匹配逻辑
"""

def keyword_matching(desc: str, text: str) -> list:
    """关键词匹配"""
    if not desc or not text:
        return []
    
    # 简单处理：按空格、逗号、顿号、以及常见中文分隔符分割
    separators = ['，', '、', ' ', '和', '与', '或', '以及']
    keywords = [desc]
    
    # 逐级分割
    for sep in separators:
        new_keywords = []
        for kw in keywords:
            new_keywords.extend([k.strip() for k in kw.split(sep) if k.strip()])
        keywords = new_keywords
    
    matched = []
    for kw in keywords:
        if len(kw) >= 2:  # 至少2个字符才匹配
            if kw.lower() in text.lower():
                matched.append(kw)
    
    return keywords, matched

# 测试
desc = "资讯收集和热点追踪"
server_desc = "获取最新新闻和热点资讯"
tool_desc = "获取指定类别的新闻"

print("描述:", desc)
print("Server 描述:", server_desc)
print("Tool 描述:", tool_desc)
print()

print("关键词匹配 Server 描述:")
keys, matched = keyword_matching(desc, server_desc)
print(f"  分词结果: {keys}")
print(f"  匹配结果: {matched}")

print("\n关键词匹配 Tool 描述:")
keys2, matched2 = keyword_matching(desc, tool_desc)
print(f"  分词结果: {keys2}")
print(f"  匹配结果: {matched2}")
