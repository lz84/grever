"""前端 API 端点全面测试"""
import urllib.request
import urllib.error
import json

BASE = "http://localhost:8090"

# 前端实际调用的 API 端点（从前端源码整理）
endpoints = [
    # === Goals ===
    ("GET", "/api/v1/goals"),
    ("GET", "/api/v1/goals/active"),
    ("POST", "/api/v1/goals", '{"name":"测试目标","description":"test","priority":"high"}'),
    # === Projects ===
    ("GET", "/api/v1/projects"),
    ("GET", "/api/v1/projects?goal_id=test"),
    # === Tasks ===
    ("GET", "/api/v1/tasks"),
    ("GET", "/api/v1/tasks?project_id=test"),
    ("GET", "/api/v1/tasks?status=pending"),
    # === Agents ===
    ("GET", "/api/v1/agents"),
    ("GET", "/api/v1/agents/online"),
    # === Scenarios ===
    ("GET", "/api/v1/scenarios"),
    ("GET", "/api/v1/scenarios?status=active"),
    # === Workflows ===
    ("GET", "/api/v1/workflows"),
    # === Traces ===
    ("GET", "/api/v1/traces"),
    ("GET", "/api/v1/traces?limit=10"),
    # === Artifacts ===
    ("GET", "/api/v1/artifacts"),
    # === Disputes ===
    ("GET", "/api/v1/disputes"),
    # === Goals tree ===
    ("GET", "/goals/test-goal-id/tree"),
    # === Workflow diagram ===
    ("GET", "/workflows/test-wf-id/diagram"),
    # === Goal decompose ===
    ("POST", "/api/v1/goals/test-goal-id/decompose", '{}'),
    # === Scenario match ===
    ("POST", "/api/v1/scenarios/match-for-goal/test-goal-id", '{}'),
    # === DAG conversation ===
    ("POST", "/api/v1/workflows/test-wf-id/dag/converse", '{"message":"test"}'),
    # === Health ===
    ("GET", "/health"),
    ("GET", "/api/health"),
    # === Dashboard stats ===
    ("GET", "/stats"),
    # === Assignments ===
    ("GET", "/api/v1/assignments"),
    # === Cognitive ===
    ("GET", "/api/v1/grasp/knowledge"),
    ("GET", "/api/v1/grasp/graph"),
    ("GET", "/api/v1/grasp/plans"),
]

results = []
ok_count = 0
err_404 = 0
err_500 = 0
err_other = 0

for ep in endpoints:
    method = ep[0]
    path = ep[1]
    body = ep[2] if len(ep) > 2 else None
    url = BASE + path
    
    try:
        data = body.encode('utf-8') if body else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header('Content-Type', 'application/json')
        resp = urllib.request.urlopen(req, timeout=5)
        code = resp.getcode()
        body_preview = resp.read()[:200].decode('utf-8', errors='replace')
        status = "OK" if code < 400 else "ERROR"
        results.append((method, path, code, status, body_preview[:100]))
        if code < 400:
            ok_count += 1
        elif code == 404:
            err_404 += 1
        elif code >= 500:
            err_500 += 1
        else:
            err_other += 1
    except urllib.error.HTTPError as e:
        code = e.code
        body_preview = e.read()[:300].decode('utf-8', errors='replace')[:100]
        results.append((method, path, code, "HTTP_ERROR", body_preview))
        if code == 404:
            err_404 += 1
        elif code >= 500:
            err_500 += 1
        else:
            err_other += 1
    except Exception as e:
        results.append((method, path, "FAIL", "EXCEPTION", str(e)[:100]))
        err_other += 1

print("=" * 120)
print(f"API 测试结果: {ok_count} OK | 404: {err_404} | 500: {err_500} | 其他错误: {err_other}")
print("=" * 120)

# Print errors first
print("\n❌ 错误端点:")
print("-" * 120)
for method, path, code, status, body in results:
    if status != "OK":
        print(f"  {method:6s} {path:60s} → {code} ({status})")
        if body:
            print(f"         响应: {body[:150]}")

print("\n✅ 正常端点:")
print("-" * 120)
for method, path, code, status, body in results:
    if status == "OK":
        print(f"  {method:6s} {path:60s} → {code}")
