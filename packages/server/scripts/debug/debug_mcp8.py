# -*- coding: utf-8 -*-
# 直接测试
desc = "资讯收集 和 热点追踪"
text = "获取最新新闻和热点资讯"

print("desc =", desc)
print("text =", text)

# 检查分词
keywords = desc.split("和")
print("split('和'):", [k for k in keywords])

# 去除空格
keywords = [k.strip() for k in keywords if k.strip()]
print("strip后:", keywords)

# 检查匹配
for kw in keywords:
    in_text = kw in text
    print(f"'{kw}' in '{text}': {in_text}")
