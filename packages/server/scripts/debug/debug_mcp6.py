# 直接测试
desc = "资讯收集 和 热点追踪"
text = "获取最新新闻和热点资讯"
sep = "和"

# 第一次分割
keywords = [desc]
new_keywords = []
for kw in keywords:
    parts = [k.strip() for k in kw.split(sep) if k.strip()]
    new_keywords.extend(parts)

print("第一次分割:", new_keywords)

# 继续处理
separators = ['，', '、', '.', '。', ' ', '和', '与', '或', '以及', '的', '是', '在']
all_keywords = [desc]

for sep in separators:
    new_ks = []
    for kw in all_keywords:
        parts = [k.strip() for k in kw.split(sep) if k.strip()]
        new_ks.extend(parts)
    all_keywords = new_ks

print("最终分词:", all_keywords)

# 检查匹配
for kw in all_keywords:
    if len(kw) >= 2:
        print(f"'{kw}' in '{text}': {kw in text}")
