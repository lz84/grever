# -*- coding: utf-8 -*-
# 直接测试 - 修改描述
desc = "资讯 和 热点"
text = "获取最新新闻和热点资讯"

print("desc =", desc)
print("text =", text)

# 逐级分割
separators = ['，', '、', '.', '。', ' ', '和', '与', '或', '以及', '的', '是', '在']
keywords = [desc]

for sep in separators:
    new_keywords = []
    for kw in keywords:
        parts = [k.strip() for k in kw.split(sep) if k.strip()]
        new_keywords.extend(parts)
    keywords = new_keywords

print("分词后:", keywords)

# 检查匹配
matched = []
for kw in keywords:
    if len(kw) >= 2:
        if kw in text:
            matched.append(kw)

print("匹配结果:", matched)
