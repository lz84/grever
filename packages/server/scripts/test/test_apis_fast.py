"""快速测试前端 API 端点"""
import urllib.request
import urllib.error
import json
import socket

BASE = "http://localhost:8090"

# 只需要测 GET，POST 后面单独测
endpoints = [
    # 核心 CRUD - GET
    ("GET", "/api/v1/goals"),
    ("GET", "/api/v1/projects"),
    ("GET", "/api/v1/tasks"),
    ("GET", "/api/v1/agents"),
    ("GET", "/api/v1/disputes"),
    ("GET", "/api/v1/scenarios"),
    ("GET", "/api/v1/workflows"),
    ("GET", "/api/v1/traces"),
    ("GET", "/api/v1/artifacts"),
    ("GET", "/api/v1/assignments"),
    ("GET", "/api/v1/discover"),
    
    # 目标分解
    ("GET", "/api/v1/goals/test-id/tree"),
    
    # 工作流
    ("GET", "/api/v1/workflows/test-id"),
    ("GET", "/api/v1/workflows/test-id/progress"),
    ("GET", "/api/v1/workflows/test-id/diagram"),
    
    # DAG 对话
    ("GET", "/api/v1/workflows/test-id/dag/conversation/history"),
    
    # 争议
    ("GET", "/api/v1/disputes/test-id"),
    ("GET", "/api/v1/disputes/test-id/detail"),
    ("GET", "/api/v1/disputes/test-id/timeline"),
    
    # 成果物
    ("GET", "/api/v1/artifacts/test-id"),
    
    # 任务
    ("GET", "/api/v1/tasks/test-id"),
    ("GET", "/api/v1/tasks/test-id/activity"),
    ("GET", "/api/v1/tasks/test-id/failure-log"),
    
    # 项目
    ("GET", "/api/v1/projects/test-id"),
    ("GET", "/api/v1/projects/test-id/progress"),
    
    # 目标
    ("GET", "/api/v1/goals/test-id"),
    
    # Agent
    ("GET", "/api/v1/discover/test-id"),
    ("GET", "/api/v1/agents/test-id/heartbeat_logs"),
    
    # Grasp
    ("GET", "/api/v1/grasp/knowledge"),
    ("GET", "/api/v1/grasp/graph"),
    ("GET", "/api/v1/grasp/plans"),
    ("GET", "/api/v1/grasp/plans/test-id"),
    ("GET", "/api/v1/grasp/cognition-assessment/test-id"),
    
    # Traces
    ("GET", "/api/v1/traces/test-id"),
    ("GET", "/api/v1/traces/test-id/step-status"),
    ("GET", "/api/v1/reports/test-id"),
    
    # Dashboard
    ("GET", "/api/v1/dashboard/stats"),
    ("GET", "/stats"),
    
    # Security
    ("GET", "/api/v1/security/audit/logs"),
    ("GET", "/api/v1/security/alerts"),
    
    # 健康
    ("GET", "/health"),
    
    # 前端有但后端可能没有
    ("GET", "/api/v1/goals/active"),
    ("GET", "/api/v1/agents/online"),
    ("GET", "/api/v1/tasks/test-id/subtasks"),
    ("GET", "/api/v1/tasks/test-id/parent"),
    ("GET", "/api/v1/scenarios/test-id/status"),
    ("GET", "/api/v1/scenarios/test-id/versions"),
    ("GET", "/api/v1/agent-matching/trust-levels/test"),
]

results = []
ok = 0
not_found = 0
server_err = 0
other_err = 0

for method, path in endpoints:
    url = BASE + path
    try:
        req = urllib.request.Request(url, method=method)
        resp = urllib.request.urlopen(req, timeout=3)
        code = resp.getcode()
        body = resp.read()[:200].decode('utf-8', errors='replace')[:100]
        results.append((method, path, code, "OK", body))
        if code < 300:
            ok += 1
        elif code == 404:
            not_found += 1
        elif code >= 500:
            server_err += 1
        else:
            other_err += 1
    except urllib.error.HTTPError as e:
        code = e.code
        body = e.read()[:200].decode('utf-8', errors='replace')[:100]
        results.append((method, path, code, "ERR", body))
        if code == 404:
            not_found += 1
        elif code >= 500:
            server_err += 1
        else:
            other_err += 1
    except Exception as e:
        results.append((method, path, "ERR", "EXCEPT", str(e)[:100]))
        other_err += 1

total = len(endpoints)
print(f"\n{'='*100}")
print(f"总计: {total} 端点 | OK: {ok} | 404: {not_found} | 500: {server_err} | 其他: {other_err}")
print(f"{'='*100}")

print("\n❌ 错误端点:")
print("-" * 100)
for method, path, code, status, body in results:
    if code not in (200, 201, 204) or status != "OK":
        print(f"  {method:6s} {path:65s} → {code}")
        if body:
            print(f"         {body[:120]}")

print(f"\n✅ 正常 ({ok}个):")
print("-" * 100)
for method, path, code, status, body in results:
    if code < 300 and status == "OK":
        print(f"  {method:6s} {path:65s} → {code}")
