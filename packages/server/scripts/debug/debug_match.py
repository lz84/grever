# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

def keyword_matching(desc: str, text: str) -> list:
    if not desc or not text:
        return []
    
    separators = ['，', '、', '.', '。', ' ', '和', '与', '或', '以及', '的', '是', '在', '对', '向', '从', '到']
    keywords = [desc]
    
    for sep in separators:
        new_keywords = []
        for kw in keywords:
            parts = [k.strip() for k in kw.split(sep) if k.strip()]
            new_keywords.extend(parts)
        keywords = new_keywords
    
    matched = []
    for kw in keywords:
        if len(kw) >= 2:
            if kw.lower() in text.lower():
                matched.append(kw)
    
    return keywords, matched

# Test
desc = "新闻资讯"
text = "获取最新新闻和热点资讯"

keywords, matched = keyword_matching(desc, text)
print(f"desc: {desc}")
print(f"text: {text}")
print(f"分词: {keywords}")
print(f"匹配: {matched}")
