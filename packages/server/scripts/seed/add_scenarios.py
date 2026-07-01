#!/usr/bin/env python3
"""Add scenario templates to industry pack."""

import json
import urllib.request

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


# Create scenarios (trailing slash required for POST)
scenarios = [
    {
        "name": "危化品泄漏应急响应场景",
        "category": "emergency",
        "description": "危化品泄漏事故的完整应急响应流程",
        "scenario_desc": "当发生危化品泄漏时，系统自动启动应急预案，协调多部门响应力量",
        "triggers": ["泄漏报警", "气体监测报警", "人工上报"],
        "steps": [
            {"phase": "侦检", "action": "确认泄漏物质和范围", "agent": "agent-leak-response"},
            {"phase": "警戒", "action": "划定警戒区域", "agent": "agent-command"},
            {"phase": "处置", "action": "实施堵漏和稀释", "agent": "agent-leak-response"},
            {"phase": "监测", "action": "实时环境监测", "agent": "agent-env-monitor"},
        ],
    },
    {
        "name": "化工园区环境监测场景",
        "category": "monitoring",
        "description": "化工园区的日常环境监测和异常预警",
        "scenario_desc": "对化工园区进行持续环境监测，识别异常指标并预警",
        "triggers": ["定时任务", "指标超阈值", "人工查询"],
        "steps": [
            {"phase": "数据采集", "action": "采集气象和气体浓度数据", "agent": "agent-env-monitor"},
            {"phase": "分析", "action": "分析数据异常", "agent": "agent-env-monitor"},
            {"phase": "预警", "action": "生成预警报告", "agent": "agent-env-monitor"},
        ],
    },
]

print("=== Creating Scenarios ===")
scenario_ids = []
for item in scenarios:
    # POST with trailing slash
    resp = api("POST", "/api/v1/scenarios/", item)
    sid = resp.get("id", "?")
    scenario_ids.append(sid)
    status = "OK" if "id" in resp else f"ERROR: {resp.get('_error', '')}"
    print(f"  {item['name']}: {status} (id={sid})")

print()

# Add scenarios to pack contents
print("=== Adding Scenarios to Pack Contents ===")
for sid in scenario_ids:
    resp = api("POST", f"/api/v1/industry-packs/{PACK_ID}/contents", {
        "pack_id": PACK_ID,
        "content_type": "scenario",
        "content_id": sid,
    })
    status = "OK" if resp.get("success") else f"ERROR: {resp.get('_error', '')}"
    print(f"  {sid}: {status}")

print()

# Update scenarios_count
current = api("GET", f"/api/v1/industry-packs/{PACK_ID}")
current_count = current.get("scenarios_count", 0)
new_count = current_count + len(scenario_ids)
resp = api("PUT", f"/api/v1/industry-packs/{PACK_ID}", {"scenarios_count": new_count})
status = "OK" if resp.get("success") else f"ERROR: {resp.get('_error', '')}"
print(f"  scenarios_count {current_count} -> {new_count}: {status}")

print()

# Final verification
resp = api("GET", f"/api/v1/industry-packs/{PACK_ID}")
print("=== Final Pack Stats ===")
for key in ["tags_count", "scenarios_count", "skills_count", "knowledge_count", "agent_schemes_count", "versions_count"]:
    print(f"  {key}: {resp.get(key)}")
