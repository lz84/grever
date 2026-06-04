# 直接测试
desc = "资讯收集 和 热点追踪"
text = "获取最新新闻和热点资讯"

print(f"desc = {repr(desc)}")
print(f"text = {repr(text)}")

# 检查分词
keywords = desc.split("和")
print(f"split('和'): {keywords}")

# 去除空格
keywords = [k.strip() for k in keywords if k.strip()]
print(f"strip后: {keywords}")

# 检查匹配
for kw in keywords:
    print(f"'{kw}' in '{text}': {kw in text}")
    print(f"'{kw}' lowercase in '{text}' lowercase: {kw.lower() in text.lower()}")
