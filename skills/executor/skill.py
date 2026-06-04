#!/usr/bin/env python3
"""
Executor (行) — Task Execution Engine v1.0

Agent claims tasks via heartbeat, executes them, and reports results.

Usage:
  python skill.py claim                  # Claim tasks via heartbeat
  python skill.py context <task_id>      # Get task context
  python skill.py complete <task_id> --result "Done"
  python skill.py fail <task_id> --error_type timeout --error_message "Timed out"
  python skill.py update <task_id> --status in_progress --progress 50
"""

import sys
import os
from typing import Optional, Dict, List

# Shared utils
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_ROOT = os.path.dirname(SKILL_DIR)
if SKILLS_ROOT not in sys.path:
    sys.path.insert(0, SKILLS_ROOT)

from _utils import NEXUS_SERVER, AGENT_ID, print_table, parse_kv_args, api_post, api_get


class TaskTrigger:
    """Claims tasks via heartbeat."""

    def __init__(self, base_url: str = None, agent_id: str = None):
        self.base_url = (base_url or os.environ.get("NEXUS_SERVER_URL", NEXUS_SERVER)).rstrip("/")
        self.agent_id = agent_id or os.environ.get("NEXUS_AGENT_ID", AGENT_ID)

    def claim(self, state: str = "idle", load: int = 10,
              current_tasks: int = 0) -> Optional[List[Dict]]:
        if not self.agent_id:
            print("Error: NEXUS_AGENT_ID not set.", file=sys.stderr)
            return []
        url = f"{self.base_url}/api/v1/agents/{self.agent_id}/heartbeat"
        payload = {"state": state, "load": load, "current_tasks": current_tasks}
        status, data = api_post(url, payload)
        if status == 200 and data:
            assigned = data.get("assigned_tasks", [])
            if data.get("load_limit_warning"):
                print("⚠️ Load limit warning", file=sys.stderr)
            return assigned
        else:
            print(f"❌ Heartbeat failed: HTTP {status}", file=sys.stderr)
            return []

    def get_context(self, task_id: str) -> Optional[Dict]:
        return api_get(f"{self.base_url}/api/v1/tasks/{task_id}/context")


class TaskExecutor:
    """Executes tasks and reports results."""

    def __init__(self, base_url: str = None):
        self.base_url = (base_url or os.environ.get("NEXUS_SERVER_URL", NEXUS_SERVER)).rstrip("/")

    def complete(self, task_id: str, result: str, artifacts: List[str] = None,
                 duration_ms: int = 0, confidence: float = 0.95,
                 issues: List[str] = None, execution_log: Dict = None) -> Optional[Dict]:
        # 确保 duration_ms > 0（Nexus API 强制要求）
        if duration_ms <= 0:
            duration_ms = 1000  # 默认 1 秒
        # 确保 execution_log 是非空字典（Nexus API 强制要求）
        if not execution_log or not isinstance(execution_log, dict):
            execution_log = {"steps": "Task executed successfully", "status": "completed"}

        payload = {
            "status": "done",
            "result": result,
            "duration_ms": duration_ms,
            "confidence": confidence,
            "execution_log": execution_log,
        }
        if artifacts:
            payload["artifacts"] = artifacts
        if issues:
            payload["issues_encountered"] = issues
        status, data = api_post(f"{self.base_url}/api/v1/tasks/{task_id}/complete", payload)
        return data if status in (200, 201) else None

    def fail(self, task_id: str, error_type: str, error_message: str,
             retry_count: int = 0, max_retries: int = 3) -> Optional[Dict]:
        payload = {
            "error_type": error_type,
            "error_message": error_message,
            "retry_count": retry_count,
            "max_retries": max_retries,
        }
        status, data = api_post(f"{self.base_url}/api/v1/tasks/{task_id}/fail", payload)
        return data if status in (200, 201) else None

    def update_status(self, task_id: str, status: str, **fields) -> Optional[Dict]:
        from _utils import api_put
        payload = {"status": status, **fields}
        code, data = api_put(f"{self.base_url}/api/v1/tasks/{task_id}", payload)
        return data if code in (200, 201) else None


# ========== CLI Commands ==========

def cmd_claim(args):
    agent_id = None
    for i, a in enumerate(args):
        if a == "--agent-id" and i + 1 < len(args):
            agent_id = args[i + 1]
    trigger = TaskTrigger(agent_id=agent_id)
    tasks = trigger.claim()
    if not tasks:
        print("No tasks assigned.")
        return
    rows = []
    for t in tasks:
        rows.append([
            t.get("id", "")[:16],
            t.get("title", "")[:40],
            t.get("status", ""),
            t.get("priority", ""),
        ])
    print_table(["ID", "Title", "Status", "Priority"], rows)


def cmd_context(args):
    if not args:
        print("Usage: skill.py context <task_id>")
        return
    trigger = TaskTrigger()
    ctx = trigger.get_context(args[0])
    if ctx:
        import json
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
    else:
        print(f"No context for {args[0]}")


def cmd_complete(args):
    if not args:
        print("Usage: skill.py complete <task_id> --result 'summary'")
        return
    fields = parse_kv_args(args, 1)
    result = fields.get("result", "Completed")
    duration_ms = int(fields.get("duration_ms", "1000"))
    confidence = float(fields.get("confidence", "0.95"))
    # execution_log 可以是 JSON 字符串或默认值
    exec_log_str = fields.get("execution_log")
    if exec_log_str:
        try:
            import json
            execution_log = json.loads(exec_log_str)
        except json.JSONDecodeError:
            execution_log = {"steps": exec_log_str, "status": "completed"}
    else:
        execution_log = {"steps": result, "status": "completed"}
    executor = TaskExecutor()
    res = executor.complete(args[0], result, duration_ms=duration_ms,
                            confidence=confidence, execution_log=execution_log)
    if res:
        print(f"[OK] Task completed: {args[0]}")
    else:
        print(f"[FAIL] Failed to complete task: {args[0]}")
        sys.exit(1)


def cmd_fail(args):
    if not args:
        print("Usage: skill.py fail <task_id> --error_type type --error_message 'msg'")
        return
    fields = parse_kv_args(args, 1)
    error_type = fields.get("error_type", "unknown")
    error_message = fields.get("error_message", "Unknown error")
    executor = TaskExecutor()
    res = executor.fail(args[0], error_type, error_message)
    if res:
        print(f"✅ Task failed: {args[0]}")
    else:
        print(f"❌ Failed to report failure: {args[0]}")
        sys.exit(1)


def cmd_update(args):
    if not args:
        print("Usage: skill.py update <task_id> --status in_progress --progress 50")
        return
    fields = parse_kv_args(args, 1)
    status = fields.get("status", "in_progress")
    executor = TaskExecutor()
    res = executor.update_status(args[0], status, **{k: v for k, v in fields.items() if k != "status"})
    if res:
        print(f"✅ Task updated: {args[0]}")
    else:
        print(f"❌ Failed to update task: {args[0]}")
        sys.exit(1)


def cmd_help(args):
    print("""
Executor (行) — Task Execution Engine

Usage: python skill.py <command> [options]

Commands:
  claim [--agent-id ID]       Claim tasks via heartbeat
  context <task_id>           Get task execution context
  complete <task_id>          Report task completion
    --result 'summary'        Result summary (default: "Completed")
    --duration_ms N           Execution duration in ms (default: 1000, must > 0)
    --confidence N            Confidence score 0-1 (default: 0.95)
    --execution_log 'json'    Execution log JSON (default: auto-generated from result)
  fail <task_id>              Report task failure
    --error_type type         Error type (timeout/execution_error/etc)
    --error_message 'msg'     Error description
  update <task_id>            Update task status
    --status in_progress      New status
    --progress 50             Progress percentage

Environment variables:
  NEXUS_SERVER_URL   Nexus API base (default: http://localhost:8090)
  NEXUS_AGENT_ID     Agent ID (required for claim)
""")


COMMANDS = {
    "claim": cmd_claim, "context": cmd_context,
    "complete": cmd_complete, "fail": cmd_fail,
    "update": cmd_update, "help": cmd_help,
}


def main():
    if len(sys.argv) < 2:
        cmd_help([])
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]
    handler = COMMANDS.get(command)
    if not handler:
        print(f"Unknown command: {command}")
        cmd_help([])
        sys.exit(1)
    handler(args)


if __name__ == "__main__":
    main()
