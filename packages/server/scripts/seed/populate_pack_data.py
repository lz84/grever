#!/usr/bin/env python3
"""Populate sample data for industry pack pack-chemical-emergency-v1."""

import json
import urllib.request
import sys

API = "http://192.168.1.9:8096"
PACK_ID = "pack-chemical-emergency-v1"


def api(method, path, data=None):
    url = API + path
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        raw = resp.read()
        return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        return {"_error": str(e), "_body": raw}


# 1. Knowledge entries
knowledge_items = [
    {
        "id": "kb-msds",
        "pack_id": PACK_ID,
        "name": "MSDS化学品安全说明书",
        "category": "chemical",
        "content": "化学品安全技术说明书(MSDS)包含16项内容，涵盖理化特性、毒性、急救措施、消防措施、泄漏处置等关键信息。",
        "tags": ["安全", "化学品"],
    },
    {
        "id": "kb-leak-procedure",
        "pack_id": PACK_ID,
        "name": "泄漏应急处置流程",
        "category": "procedure",
        "content": "发现泄漏后立即报告，启动应急预案，疏散人员，设置警戒区域，使用专用堵漏器材处置。",
        "tags": ["应急", "泄漏"],
    },
    {
        "id": "kb-diffusion-model",
        "pack_id": PACK_ID,
        "name": "有毒有害气体扩散模型",
        "category": "model",
        "content": "高斯烟羽模型适用于连续源扩散计算，需输入风速、稳定度等级、源强等参数。",
        "tags": ["模型", "扩散"],
    },
    {
        "id": "kb-fire-guide",
        "pack_id": PACK_ID,
        "name": "消防灭火剂选择指南",
        "category": "chemical",
        "content": "根据燃烧物质类型选择灭火剂：A类火灾用水，B类用泡沫/干粉，C类用CO2/干粉，D类用专用灭火剂。",
        "tags": ["消防", "灭火剂"],
    },
    {
        "id": "kb-multi-agency",
        "pack_id": PACK_ID,
        "name": "多部门协同响应机制",
        "category": "procedure",
        "content": "化工事故响应需应急、环保、消防、医疗等多部门联动，建立统一指挥体系。",
        "tags": ["协同", "指挥"],
    },
]

print("=== Creating Knowledge Entries ===")
for item in knowledge_items:
    resp = api("POST", "/api/v1/knowledge", item)
    status = "OK" if "id" in resp else f"ERROR: {resp.get('_error', '')}"
    print(f"  {item['name']}: {status}")

print()

# 2. Agent Schemes
agent_schemes = [
    {
        "name": "危化品泄漏应急处置智能体",
        "industry": "chemical-emergency",
        "description": "用于危化品泄漏事故的智能应急处置方案，包含泄漏评估、扩散预测、疏散建议等核心能力。",
        "target_audience": "化工园区应急指挥中心",
        "scenario_tags": ["emergency-response", "leak-handling"],
        "agent_id": "agent-leak-response",
        "pack_id": PACK_ID,
    },
    {
        "name": "环境监测数据分析智能体",
        "industry": "chemical-emergency",
        "description": "实时分析环境监测数据，识别异常指标，预测污染扩散趋势。",
        "target_audience": "环保局监测站",
        "scenario_tags": ["environmental-monitoring", "data-analysis"],
        "agent_id": "agent-env-monitor",
        "pack_id": PACK_ID,
    },
    {
        "name": "应急指挥调度智能体",
        "industry": "chemical-emergency",
        "description": "统筹协调多部门应急力量，生成调度方案，跟踪任务执行进度。",
        "target_audience": "应急指挥中心",
        "scenario_tags": ["incident-command", "multi-agency-coordination"],
        "agent_id": "agent-command",
        "pack_id": PACK_ID,
    },
]

print("=== Creating Agent Schemes ===")
for item in agent_schemes:
    resp = api("POST", "/api/v1/agent-schemes", item)
    status = "OK" if "id" in resp else f"ERROR: {resp.get('_error', '')}"
    print(f"  {item['name']}: {status}")

print()

# 3. Pack Skills
skills = [
    {
        "id": "skill-diffusion",
        "name": "扩散模拟计算",
        "description": "基于高斯烟羽模型计算有害气体扩散范围和浓度分布",
        "pack_id": PACK_ID,
        "input_schema": {"type": "object", "properties": {"chemical": {"type": "string"}, "wind_speed": {"type": "number"}, "stability_class": {"type": "string"}}},
        "output_schema": {"type": "object", "properties": {"concentration_map": {"type": "string"}, "evacuation_radius": {"type": "number"}}},
        "required_tags": ["chem:diffusion-modeling"],
    },
    {
        "id": "skill-msds",
        "name": "MSDS解析",
        "description": "自动解析化学品安全说明书(MSDS)，提取关键安全信息",
        "pack_id": PACK_ID,
        "input_schema": {"type": "object", "properties": {"document": {"type": "string"}, "format": {"type": "string"}}},
        "output_schema": {"type": "object", "properties": {"hazard_class": {"type": "string"}, "first_aid": {"type": "string"}}},
        "required_tags": ["chem:msds-parsing"],
    },
    {
        "id": "skill-leak-rate",
        "name": "泄漏速率计算",
        "description": "根据泄漏孔径、压力、物性等参数计算泄漏速率和总量",
        "pack_id": PACK_ID,
        "input_schema": {"type": "object", "properties": {"orifice_diameter": {"type": "number"}, "pressure": {"type": "number"}}},
        "output_schema": {"type": "object", "properties": {"leak_rate": {"type": "number"}, "total_leakage": {"type": "number"}}},
        "required_tags": ["chem:leak-rate-calculation"],
    },
    {
        "id": "skill-weather",
        "name": "气象数据分析",
        "description": "分析风速、风向、温度、湿度等气象数据，为扩散模拟提供输入",
        "pack_id": PACK_ID,
        "input_schema": {"type": "object", "properties": {"station_id": {"type": "string"}, "time_range": {"type": "string"}}},
        "output_schema": {"type": "object", "properties": {"wind_speed": {"type": "number"}, "stability_class": {"type": "string"}}},
        "required_tags": ["chem:weather-analysis"],
    },
]

print("=== Creating Pack Skills ===")
for item in skills:
    resp = api("POST", "/api/v1/pack-skills", item)
    status = "OK" if "id" in resp else f"ERROR: {resp.get('_error', '')}"
    print(f"  {item['name']}: {status}")

print()

# 4. Update tags_count (pack already has tags in contents)
print("=== Updating tags_count ===")
# Get the pack contents that are tags
pack_resp = api("GET", f"/api/v1/industry-packs/{PACK_ID}")
tag_contents = [c for c in pack_resp.get("contents", []) if c.get("content_type") == "tag"]
tags_count = len(tag_contents)
resp = api("PUT", f"/api/v1/industry-packs/{PACK_ID}", {"tags_count": tags_count})
status = "OK" if "tags_count" in str(resp) else f"ERROR: {resp.get('_error', '')}"
print(f"  tags_count updated to {tags_count}: {status}")

print()

# 5. Verify final counts
resp = api("GET", f"/api/v1/industry-packs/{PACK_ID}")
print("=== Final Pack Stats ===")
for key in [
    "tags_count",
    "scenarios_count",
    "skills_count",
    "knowledge_count",
    "agent_schemes_count",
    "versions_count",
]:
    print(f"  {key}: {resp.get(key)}")
