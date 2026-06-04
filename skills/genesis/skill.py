#!/usr/bin/env python3
"""
Genesis (生) — Goal Decomposition Engine v1.0

Breaks complex goals into executable Project/Task trees with DAG dependencies.

Usage:
  python skill.py decompose "Build a disaster response system"
  python skill.py decompose "goal text" --no-llm --format json -o output.json
  python skill.py list
"""

import sys
import os
import json
import re
import argparse
from typing import Optional, List, Dict

# Shared utils — skills/ is our parent dir
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_ROOT = os.path.dirname(SKILL_DIR)
if SKILLS_ROOT not in sys.path:
    sys.path.insert(0, SKILLS_ROOT)

from _utils import (
    api_post, api_get, NEXUS_SERVER,
    LLM_API, LLM_MODEL, LLM_API_KEY,
    parse_kv_args,
)

# ========== LLM Decomposition ==========
DECOMPOSE_SYSTEM_PROMPT = """You are a task decomposition expert. Break complex goals into executable subtasks.

Rules:
1. Each subtask: 1-4 hours granularity
2. Identify dependencies (finish-to-start)
3. Identify parallelizable tasks
4. Assign priority (P0/P1/P2)

Output strictly valid JSON:
{"subtasks":[{"title":"...","description":"...","priority":"P0|P1|P2","estimated_hours":2.0,"required_capabilities":["coding"],"depends_on":[],"can_parallel_with":[]}],"estimated_total_hours":0.0}

Only output JSON, nothing else."""


def _call_llm(messages: List[Dict]) -> Optional[str]:
    try:
        import requests as _http
    except ImportError:
        return None
    if not LLM_API:
        return None
    try:
        r = _http.post(
            f"{LLM_API}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"},
            json={"model": LLM_MODEL, "messages": messages, "max_tokens": 3000, "temperature": 0.7},
            timeout=60
        )
        if r.ok:
            return r.json()["choices"][0]["message"]["content"]
    except Exception:
        pass
    return None


def decompose_with_llm(goal_text: str) -> Optional[Dict]:
    messages = [
        {"role": "system", "content": DECOMPOSE_SYSTEM_PROMPT},
        {"role": "user", "content": f"Decompose this goal into subtasks:\n{goal_text}"}
    ]
    response = _call_llm(messages)
    if not response:
        return None
    try:
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        return json.loads(response)
    except (json.JSONDecodeError, KeyError):
        return None


def decompose_pattern_based(goal_text: str) -> Dict:
    """Fallback when LLM is unavailable."""
    goal_lower = goal_text.lower()
    if any(k in goal_lower for k in ["project", "init", "setup"]):
        return {
            "subtasks": [
                {"title": "[P0] Project planning and structure", "description": f"Plan structure for: {goal_text}", "priority": "P0", "estimated_hours": 2.0, "required_capabilities": ["architecture"], "depends_on": [], "can_parallel_with": []},
                {"title": "[P1] Core module development", "description": f"Implement core features for: {goal_text}", "priority": "P1", "estimated_hours": 4.0, "required_capabilities": ["coding"], "depends_on": ["task-1"], "can_parallel_with": []},
                {"title": "[P2] Integration testing", "description": f"Test and verify: {goal_text}", "priority": "P2", "estimated_hours": 2.0, "required_capabilities": ["testing"], "depends_on": ["task-2"], "can_parallel_with": []},
            ],
            "estimated_total_hours": 8.0,
        }
    elif any(k in goal_lower for k in ["analyze", "research", "report"]):
        return {
            "subtasks": [
                {"title": "[P0] Information gathering", "description": f"Collect data for: {goal_text}", "priority": "P0", "estimated_hours": 2.0, "required_capabilities": ["research"], "depends_on": [], "can_parallel_with": []},
                {"title": "[P1] Deep analysis", "description": f"Analyze findings for: {goal_text}", "priority": "P1", "estimated_hours": 3.0, "required_capabilities": ["analysis"], "depends_on": ["task-1"], "can_parallel_with": []},
                {"title": "[P2] Summary report", "description": f"Write report for: {goal_text}", "priority": "P2", "estimated_hours": 1.0, "required_capabilities": ["writing"], "depends_on": ["task-2"], "can_parallel_with": []},
            ],
            "estimated_total_hours": 6.0,
        }
    else:
        return {
            "subtasks": [
                {"title": f"[P0] Execute: {goal_text[:50]}", "description": f"Execute: {goal_text}", "priority": "P0", "estimated_hours": 2.0, "required_capabilities": ["general"], "depends_on": [], "can_parallel_with": []},
            ],
            "estimated_total_hours": 2.0,
        }


# ========== Grasp Integration ==========
def _inject_grasp_context(goal_text: str) -> List[Dict]:
    """Retrieve related knowledge from Grasp and inject into decomposition context."""
    grasp_api = os.environ.get("GRASP_API", "")
    if not grasp_api:
        return []
    try:
        import requests as _http
        r = _http.get(f"{grasp_api}/api/v1/grasp/retrieve", params={"q": goal_text[:100]}, timeout=5)
        if r.ok:
            data = r.json()
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


# ========== CLI Commands ==========

def cmd_decompose(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("goal", nargs="*", help="Goal text")
    parser.add_argument("--no-llm", action="store_true", help="Force pattern-based")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("-o", "--output", help="Save to file")
    parsed, _ = parser.parse_known_args(args)

    if not parsed.goal:
        print('Usage: skill.py decompose "goal text" [--no-llm] [--format json] [-o file]')
        return

    goal = " ".join(parsed.goal)
    print(f"Decomposing: {goal}")

    # Try to inject Grasp context
    grasp_context = _inject_grasp_context(goal)
    if grasp_context:
        print(f"  📚 Injected {len(grasp_context)} knowledge entries from Grasp")

    result = decompose_with_llm(goal) if not parsed.no_llm else None
    if not result:
        result = decompose_pattern_based(goal)
        print("  (using pattern-based decomposition)")

    subtasks = result.get("subtasks", [])
    total = result.get("estimated_total_hours", 0)

    if parsed.format == "json":
        output = json.dumps(result, ensure_ascii=False, indent=2)
        if parsed.output:
            with open(parsed.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Saved to {parsed.output}")
        else:
            print(output)
    else:
        print(f"\n{'='*60}")
        print(f"Goal: {goal}")
        print(f"Decomposed into {len(subtasks)} subtasks, estimated {total}h")
        print(f"{'='*60}\n")
        for i, st in enumerate(subtasks, 1):
            print(f"  {i}. {st.get('title')} [{st.get('priority','P1')}] ({st.get('estimated_hours',0)}h)")
            desc = st.get("description", "")
            print(f"     {desc[:80]}...")
            if st.get("depends_on"):
                print(f"     ← depends on: {', '.join(st['depends_on'])}")
            print()
        if parsed.output:
            with open(parsed.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"Saved to {parsed.output}")


def cmd_list_decompose(args):
    """List decomposition history."""
    NEXUS_ROOT = os.environ.get("NEXUS_ROOT", os.path.join(SKILLS_ROOT, "..", ".."))
    memory_dir = os.path.join(NEXUS_ROOT, "memory", "reins")
    path = os.path.join(memory_dir, "decompositions.jsonl")
    if not os.path.exists(path):
        print("No decomposition history.")
        return
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    print(f"\nDecomposition history: {len(records)} records\n")
    for r in records[-5:]:
        print(f"  {r.get('goal_id')}: {r.get('goal_text','')[:50]}")
        print(f"    → {len(r.get('subtasks',[]))} subtasks, {r.get('estimated_total_hours',0)}h")


def cmd_help(args):
    print("""
Genesis (生) — Goal Decomposition Engine

Usage: python skill.py <command> [options]

Commands:
  decompose "goal"       Decompose goal into subtasks
  list                   Show decomposition history
  help                   Show this help

Options:
  --no-llm               Force pattern-based decomposition
  --format json|text     Output format (default: text)
  -o, --output FILE      Save result to file

Environment variables:
  NEXUS_SERVER_URL       Nexus API base (default: http://localhost:8090)
  LLM_API                LLM API URL for intelligent decomposition
  LLM_MODEL              LLM model name (default: qwen3-30b-a3b-fp8)
  LLM_API_KEY            LLM API key
  GRASP_API              Grasp knowledge API URL (optional, for context injection)
""")


# ========== Entry Point ==========
COMMANDS = {
    "decompose": cmd_decompose,
    "list": cmd_list_decompose,
    "help": cmd_help,
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
