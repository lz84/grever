"""前端 API 端点全面测试 - 基于前端实际调用"""
import urllib.request
import urllib.error
import json

BASE = "http://localhost:8090"

# 按前端 api.ts 实际调用的端点，加后端路由没有的
endpoints = [
    # === 核心 CRUD ===
    ("GET", "/api/v1/goals", None),
    ("POST", "/api/v1/goals", json.dumps({"title": "test", "description": "test"})),
    ("GET", "/api/v1/projects", None),
    ("POST", "/api/v1/projects", json.dumps({"name": "test", "description": "test"})),
    ("GET", "/api/v1/tasks", None),
    ("POST", "/api/v1/tasks", json.dumps({"title": "test", "description": "test"})),
    ("GET", "/api/v1/agents", None),
    ("POST", "/api/v1/agents", json.dumps({"agent_id": "test", "name": "test", "capabilities": []})),
    ("GET", "/api/v1/disputes", None),
    ("POST", "/api/v1/disputes", json.dumps({"dispute_type": "test", "description": "test", "involved_agents": []})),
    ("GET", "/api/v1/scenarios", None),
    ("POST", "/api/v1/scenarios", json.dumps({"name": "test", "category": "test", "scenario_desc": "test"})),
    ("GET", "/api/v1/workflows", None),
    ("GET", "/api/v1/traces", None),
    ("GET", "/api/v1/artifacts", None),
    ("GET", "/api/v1/assignments", None),
    
    # === 目标分解 ===
    ("POST", "/api/v1/goals/test-id/decompose", json.dumps({})),
    ("POST", "/api/v1/goals/test-id/auto-decompose", json.dumps({})),
    
    # === 场景匹配 & 实例化 ===
    ("POST", "/api/v1/scenarios/match-for-goal/test-id", json.dumps({})),
    ("POST", "/api/v1/scenarios/test-id/instantiate-workflow", json.dumps({})),
    
    # === Agent 匹配 ===
    ("POST", "/api/v1/agent-matching/match", json.dumps({"scenario_id": "test"})),
    ("GET", "/api/v1/agent-matching/trust-levels/test", None),
    
    # === 工作流 ===
    ("POST", "/api/v1/workflows/from-goal", None),
    ("GET", "/api/v1/workflows/test-id", None),
    ("POST", "/api/v1/workflows/test-id/execute", None),
    ("POST", "/api/v1/workflows/test-id/steps", json.dumps({"name": "test"})),
    ("GET", "/api/v1/workflows/test-id/progress", None),
    
    # === 目标树 ===
    ("GET", "/api/v1/goals/test-id/tree", None),
    
    # === 工作流图 ===
    ("GET", "/api/v1/workflows/test-id/diagram", None),
    
    # === DAG 对话 ===
    ("POST", "/api/v1/workflows/test-id/dag/chat", json.dumps({"message": "test"})),
    ("POST", "/api/v1/workflows/test-id/dag/converse", json.dumps({"message": "test"})),
    ("GET", "/api/v1/workflows/test-id/dag/conversation/history", None),
    
    # === 争议管理 ===
    ("GET", "/api/v1/disputes/test-id", None),
    ("GET", "/api/v1/disputes/test-id/detail", None),
    ("POST", "/api/v1/disputes/test-id/discuss", json.dumps({"content": "test"})),
    ("PATCH", "/api/v1/disputes/test-id/resolve", json.dumps({"resolution": "test"})),
    ("POST", "/api/v1/disputes/test-id/arbitrate", json.dumps({"decision": "test"})),
    ("GET", "/api/v1/disputes/test-id/timeline", None),
    
    # === 成果物 ===
    ("GET", "/api/v1/artifacts/test-id", None),
    ("GET", "/api/v1/artifacts/test-id/download", None),
    
    # === 任务 ===
    ("GET", "/api/v1/tasks/test-id", None),
    ("POST", "/api/v1/tasks/test-id/complete", json.dumps({"status": "done"})),
    ("POST", "/api/v1/tasks/test-id/fail", json.dumps({"error_type": "test", "error_message": "test", "retry_count": 0, "max_retries": 3})),
    ("POST", "/api/v1/tasks/test-id/retry", json.dumps({})),
    ("PATCH", "/api/v1/tasks/test-id/block", json.dumps({})),
    ("PATCH", "/api/v1/tasks/test-id/unblock", json.dumps({})),
    ("GET", "/api/v1/tasks/test-id/activity", None),
    ("GET", "/api/v1/tasks/test-id/failure-log", None),
    
    # === 项目 ===
    ("GET", "/api/v1/projects/test-id", None),
    ("GET", "/api/v1/projects/test-id/progress", None),
    ("POST", "/api/v1/projects/test-id/members", json.dumps({"member_id": "test"})),
    
    # === 目标 ===
    ("GET", "/api/v1/goals/test-id", None),
    ("PATCH", "/api/v1/goals/test-id/status", json.dumps({"status": "in_progress"})),
    ("PATCH", "/api/v1/goals/test-id/transition", json.dumps({"new_status": "in_progress"})),
    
    # === Agent ===
    ("GET", "/api/v1/discover", None),
    ("GET", "/api/v1/discover/test-id", None),
    ("DELETE", "/api/v1/agents/test-id", None),
    ("POST", "/api/v1/agents/test-id/heartbeat", json.dumps({})),
    ("GET", "/api/v1/agents/test-id/heartbeat_logs", None),
    ("PATCH", "/api/v1/agents/test-id/trigger_mode", json.dumps({"trigger_mode": "sse"})),
    
    # === Grasp ===
    ("GET", "/api/v1/grasp/knowledge", None),
    ("GET", "/api/v1/grasp/graph", None),
    ("GET", "/api/v1/grasp/plans", None),
    ("POST", "/api/v1/grasp/plans", json.dumps({"name": "test"})),
    ("GET", "/api/v1/grasp/plans/test-id", None),
    ("GET", "/api/v1/grasp/cognition-assessment/test-id", None),
    
    # === Traces ===
    ("POST", "/api/v1/traces", json.dumps({"task_id": "test", "workflow_id": "test", "task_title": "test"})),
    ("GET", "/api/v1/traces/test-id", None),
    ("PATCH", "/api/v1/traces/test-id/complete", json.dumps({"final_state": "done", "success": True})),
    ("GET", "/api/v1/traces/test-id/step-status", None),
    ("GET", "/api/v1/reports/test-id", None),
    
    # === Dashboard ===
    ("GET", "/api/v1/dashboard/stats", None),
    ("GET", "/stats", None),
    
    # === Security ===
    ("GET", "/api/v1/security/audit/logs", None),
    ("GET", "/api/v1/security/alerts", None),
    ("POST", "/api/v1/security/alerts", json.dumps({"title": "test", "level": "warning", "category": "test"})),
    
    # === 健康 ===
    ("GET", "/health", None),
    ("GET", "/api/health", None),
    
    # === 前端 api.ts 里调用了但后端可能没有 ===
    ("GET", "/api/v1/goals/active", None),
    ("GET", "/api/v1/agents/online", None),
    ("PATCH", "/api/v1/tasks/test-id/status", json.dumps({"status": "done"})),
    ("GET", "/api/v1/tasks/test-id/subtasks", None),
    ("GET", "/api/v1/tasks/test-id/parent", None),
    ("POST", "/api/v1/goals/test-id/decompose/submit", json.dumps({"tasks": []})),
    ("GET", "/api/v1/scenarios/test-id/status", None),
    ("PATCH", "/api/v1/scenarios/test-id/status", json.dumps({"status": "active"})),
    ("POST", "/api/v1/scenarios/test-id/feedback", json.dumps({"rating": 5})),
    ("GET", "/api/v1/scenarios/test-id/versions", None),
]

results = []
ok_count = 0
err_404 = 0
err_500 = 0
err_other = 0

for method, path, body in endpoints:
    url = BASE + path
    try:
        data = body.encode('utf-8') if body else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header('Content-Type', 'application/json')
        resp = urllib.request.urlopen(req, timeout=5)
        code = resp.getcode()
        resp_body = resp.read()[:300].decode('utf-8', errors='replace')
        results.append((method, path, code, "OK", resp_body[:150]))
        if code < 300:
            ok_count += 1
        elif code == 404:
            err_404 += 1
        elif code >= 500:
            err_500 += 1
        else:
            err_other += 1
    except urllib.error.HTTPError as e:
        code = e.code
        resp_body = e.read()[:300].decode('utf-8', errors='replace')[:150]
        results.append((method, path, code, "HTTP_ERROR", resp_body))
        if code == 404:
            err_404 += 1
        elif code >= 500:
            err_500 += 1
        else:
            err_other += 1
    except Exception as e:
        results.append((method, path, "FAIL", "EXCEPTION", str(e)[:150]))
        err_other += 1

print("=" * 130)
print(f"总计: {len(endpoints)} 端点 | {ok_count} 正常(<300) | 404: {err_404} | 500: {err_500} | 其他: {err_other}")
print("=" * 130)

print("\n❌ 错误端点 (404/500/其他):")
print("-" * 130)
for method, path, code, status, body in results:
    if code not in (200, 201, 204) or status != "OK":
        print(f"  {method:6s} {path:65s} → {code} [{status}]")
        if body:
            detail = body[:120].replace('\n', ' ')
            print(f"         {detail}")

print(f"\n✅ 正常端点 ({ok_count} 个):")
print("-" * 130)
for method, path, code, status, body in results:
    if code < 300 and status == "OK":
        print(f"  {method:6s} {path:65s} → {code}")
