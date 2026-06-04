#!/usr/bin/env python3
"""
Reins (缰) — Entity CRUD & State Machine v1.0

Goal/Project/Task CRUD operations. Decomposition → genesis. Lifecycle → pulse.

Usage:
  python skill.py goal-list [--status active]
  python skill.py goal-create "Build a system" --priority high
  python skill.py task-list --project-id proj-xxx --status todo
  python skill.py task-complete task-xxx --result "Done"
"""

import sys
import os
import argparse
from typing import Optional, List, Dict, Any

# Shared utils
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_ROOT = os.path.dirname(SKILL_DIR)
if SKILLS_ROOT not in sys.path:
    sys.path.insert(0, SKILLS_ROOT)

from _utils import (
    api_get, api_post, api_put, api_delete, NEXUS_SERVER,
    print_table, parse_kv_args,
)


class NexusAPI:
    """CRUD for Goals, Projects, Tasks."""

    def __init__(self, base_url: str = None):
        self.base = (base_url or NEXUS_SERVER).rstrip("/")

    # Goals
    def goal_list(self, status: str = None) -> List[Dict]:
        data = api_get(f"{self.base}/api/v1/goals")
        if not data or not isinstance(data, list):
            return []
        return [g for g in data if not status or g.get("status") == status]

    def goal_create(self, title: str, description: str = "", priority: str = "medium",
                    status: str = "active", due_date: str = None) -> Optional[Dict]:
        payload = {"title": title, "description": description, "priority": priority, "status": status}
        if due_date:
            payload["due_date"] = due_date
        code, data = api_post(f"{self.base}/api/v1/goals", payload)
        return data if code in (200, 201) else None

    def goal_update(self, goal_id: str, **fields) -> Optional[Dict]:
        code, data = api_put(f"{self.base}/api/v1/goals/{goal_id}", fields)
        return data if code in (200, 201) else None

    def goal_delete(self, goal_id: str) -> bool:
        return api_delete(f"{self.base}/api/v1/goals/{goal_id}") in (200, 204)

    # Projects
    def project_list(self, goal_id: str = None) -> List[Dict]:
        data = api_get(f"{self.base}/api/v1/projects")
        if not data or not isinstance(data, list):
            return []
        return [p for p in data if not goal_id or p.get("goal_id") == goal_id]

    def project_create(self, name: str, goal_id: str, description: str = "",
                       priority: str = "medium") -> Optional[Dict]:
        payload = {"name": name, "goal_id": goal_id, "description": description,
                   "priority": priority, "status": "active"}
        code, data = api_post(f"{self.base}/api/v1/projects", payload)
        return data if code in (200, 201) else None

    def project_update(self, project_id: str, **fields) -> Optional[Dict]:
        code, data = api_put(f"{self.base}/api/v1/projects/{project_id}", fields)
        return data if code in (200, 201) else None

    def project_delete(self, project_id: str) -> bool:
        return api_delete(f"{self.base}/api/v1/projects/{project_id}") in (200, 204)

    # Tasks
    def task_list(self, project_id: str = None, goal_id: str = None, status: str = None) -> List[Dict]:
        data = api_get(f"{self.base}/api/v1/tasks")
        if not data or not isinstance(data, list):
            return []
        if project_id:
            data = [t for t in data if t.get("project_id") == project_id]
        if goal_id:
            data = [t for t in data if t.get("goal_id") == goal_id]
        if status:
            data = [t for t in data if t.get("status") == status]
        return data

    def task_create(self, title: str, project_id: str = None, goal_id: str = None,
                    description: str = "", priority: str = "medium",
                    category: str = None, due_date: str = None) -> Optional[Dict]:
        payload = {"title": title, "description": description, "priority": priority}
        if project_id:
            payload["project_id"] = project_id
        if goal_id:
            payload["goal_id"] = goal_id
        if category:
            payload["category"] = category
        if due_date:
            payload["due_date"] = due_date
        code, data = api_post(f"{self.base}/api/v1/tasks", payload)
        return data if code in (200, 201) else None

    def task_update(self, task_id: str, **fields) -> Optional[Dict]:
        code, data = api_put(f"{self.base}/api/v1/tasks/{task_id}", fields)
        return data if code in (200, 201) else None

    def task_complete(self, task_id: str, result: str = "") -> Optional[Dict]:
        return self.task_update(task_id, status="completed", result=result)

    def task_delete(self, task_id: str) -> bool:
        return api_delete(f"{self.base}/api/v1/tasks/{task_id}") in (200, 204)

    # Verifier
    def set_verifier(self, task_id: str, verifier_agent_id: str) -> Optional[Dict]:
        code, data = api_post(f"{self.base}/api/v1/tasks/{task_id}/verifier",
                              {"verifier_agent_id": verifier_agent_id})
        return data if code in (200, 201) else None

    def get_verifier(self, task_id: str) -> Optional[Dict]:
        return api_get(f"{self.base}/api/v1/tasks/{task_id}/verifier")

    # Task Actions
    def task_retry(self, task_id: str) -> tuple:
        return api_post(f"{self.base}/api/v1/tasks/{task_id}/retry", {})

    def task_fail(self, task_id: str, error_message: str = "", error_type: str = "") -> Optional[Dict]:
        code, data = api_post(f"{self.base}/api/v1/tasks/{task_id}/fail",
                              {"error_message": error_message, "error_type": error_type})
        return data if code in (200, 201) else None

    def task_review(self, task_id: str, action: str, reason: str = "") -> Optional[Dict]:
        code, data = api_post(f"{self.base}/api/v1/tasks/{task_id}/review",
                              {"action": action, "reason": reason})
        return data if code in (200, 201) else None


# ========== CLI Commands ==========

def cmd_goal_list(args):
    api = NexusAPI()
    status_filter = None
    if "--status" in args:
        idx = args.index("--status")
        if idx + 1 < len(args):
            status_filter = args[idx + 1]
    goals = api.goal_list(status=status_filter)
    if not goals:
        print("No goals.")
        return
    rows = [[g.get("id", "")[:16], g.get("title", ""), g.get("status", ""),
             g.get("priority", ""), str(g.get("progress", 0)) + "%"] for g in goals]
    print_table(["ID", "Title", "Status", "Priority", "Progress"], rows)


def cmd_goal_create(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("title")
    parser.add_argument("--description", default="")
    parser.add_argument("--priority", default="medium")
    parser.add_argument("--due-date", default=None)
    parsed, _ = parser.parse_known_args(args)
    api = NexusAPI()
    result = api.goal_create(parsed.title, parsed.description, parsed.priority, due_date=parsed.due_date)
    if result:
        print(f"✅ Goal created: {result.get('id')} — {parsed.title}")
    else:
        print("❌ Failed to create goal.")
        sys.exit(1)


def cmd_goal_update(args):
    if not args:
        print("Usage: skill.py goal-update <goal_id> --status <status> --progress <num>")
        return
    goal_id = args[0]
    fields = parse_kv_args(args, 1)
    if "progress" in fields:
        try:
            fields["progress"] = float(fields["progress"])
        except ValueError:
            pass
    api = NexusAPI()
    result = api.goal_update(goal_id, **fields)
    if result:
        print(f"✅ Goal updated: {goal_id}")
    else:
        print("❌ Failed to update goal.")
        sys.exit(1)


def cmd_goal_delete(args):
    if not args:
        print("Usage: skill.py goal-delete <goal_id>")
        return
    api = NexusAPI()
    if api.goal_delete(args[0]):
        print(f"✅ Goal deleted: {args[0]}")
    else:
        print("❌ Failed to delete goal.")
        sys.exit(1)


def cmd_project_list(args):
    api = NexusAPI()
    goal_id = None
    if "--goal-id" in args:
        idx = args.index("--goal-id")
        if idx + 1 < len(args):
            goal_id = args[idx + 1]
    projects = api.project_list(goal_id=goal_id)
    if not projects:
        print("No projects.")
        return
    rows = [[p.get("id", "")[:16], p.get("name", ""), p.get("status", ""),
             p.get("priority", ""), p.get("goal_id", "")[:16]] for p in projects]
    print_table(["ID", "Name", "Status", "Priority", "Goal ID"], rows)


def cmd_project_create(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--goal-id", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--priority", default="medium")
    parsed, _ = parser.parse_known_args(args)
    api = NexusAPI()
    result = api.project_create(parsed.name, parsed.goal_id, parsed.description, parsed.priority)
    if result:
        print(f"✅ Project created: {result.get('id')} — {parsed.name}")
    else:
        print("❌ Failed to create project.")
        sys.exit(1)


def cmd_project_update(args):
    if not args:
        print("Usage: skill.py project-update <project_id> --status <status>")
        return
    fields = parse_kv_args(args, 1)
    api = NexusAPI()
    result = api.project_update(args[0], **fields)
    if result:
        print(f"✅ Project updated: {args[0]}")
    else:
        print("❌ Failed to update project.")
        sys.exit(1)


def cmd_project_delete(args):
    if not args:
        print("Usage: skill.py project-delete <project_id>")
        return
    api = NexusAPI()
    if api.project_delete(args[0]):
        print(f"✅ Project deleted: {args[0]}")
    else:
        print("❌ Failed to delete project.")
        sys.exit(1)


def cmd_task_list(args):
    api = NexusAPI()
    project_id = goal_id = status = None
    for flag in ("--project-id", "--goal-id", "--status"):
        if flag in args:
            idx = args.index(flag)
            if idx + 1 < len(args):
                if flag == "--project-id":
                    project_id = args[idx + 1]
                elif flag == "--goal-id":
                    goal_id = args[idx + 1]
                elif flag == "--status":
                    status = args[idx + 1]
    tasks = api.task_list(project_id=project_id, goal_id=goal_id, status=status)
    if not tasks:
        print("No tasks.")
        return
    rows = [[t.get("id", "")[:16], t.get("title", ""), t.get("status", ""),
             t.get("priority", ""), t.get("assigned_agent", "") or "-"] for t in tasks]
    print_table(["ID", "Title", "Status", "Priority", "Assignee"], rows)


def cmd_task_create(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("title")
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--goal-id", default=None)
    parser.add_argument("--description", default="")
    parser.add_argument("--priority", default="medium")
    parser.add_argument("--category", default=None)
    parser.add_argument("--due-date", default=None)
    parsed, _ = parser.parse_known_args(args)
    api = NexusAPI()
    result = api.task_create(parsed.title, parsed.project_id, parsed.goal_id,
                             parsed.description, parsed.priority,
                             category=parsed.category, due_date=parsed.due_date)
    if result:
        print(f"✅ Task created: {result.get('id')} — {parsed.title}")
    else:
        print("❌ Failed to create task.")
        sys.exit(1)


def cmd_task_update(args):
    if not args:
        print("Usage: skill.py task-update <task_id> --status <status> --result <text>")
        return
    fields = parse_kv_args(args, 1)
    api = NexusAPI()
    result = api.task_update(args[0], **fields)
    if result:
        print(f"✅ Task updated: {args[0]}")
    else:
        print("❌ Failed to update task.")
        sys.exit(1)


def cmd_task_complete(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    parser.add_argument("--result", default="Completed")
    parsed, _ = parser.parse_known_args(args)
    api = NexusAPI()
    result = api.task_complete(parsed.task_id, parsed.result)
    if result:
        print(f"✅ Task completed: {parsed.task_id}")
    else:
        print("❌ Failed to complete task.")
        sys.exit(1)


def cmd_task_delete(args):
    if not args:
        print("Usage: skill.py task-delete <task_id>")
        return
    api = NexusAPI()
    if api.task_delete(args[0]):
        print(f"✅ Task deleted: {args[0]}")
    else:
        print("❌ Failed to delete task.")
        sys.exit(1)


def cmd_task_retry(args):
    if not args:
        print("Usage: skill.py task-retry <task_id>")
        return
    api = NexusAPI()
    code, data = api.task_retry(args[0])
    if code in (200, 201):
        print(f"✅ Task retried: {args[0]}")
    else:
        print(f"❌ Failed to retry task: HTTP {code}")
        sys.exit(1)


def cmd_task_fail(args):
    if not args:
        print("Usage: skill.py task-fail <task_id> --error_message 'msg' --error_type 'type'")
        return
    fields = parse_kv_args(args, 1)
    api = NexusAPI()
    result = api.task_fail(args[0], **fields)
    if result:
        print(f"✅ Task failed: {args[0]}")
    else:
        print("❌ Failed to report task failure.")
        sys.exit(1)


def cmd_task_review(args):
    if not args:
        print("Usage: skill.py task-review <task_id> --action approve|reject --reason 'reason'")
        return
    fields = parse_kv_args(args, 1)
    api = NexusAPI()
    result = api.task_review(args[0], **fields)
    if result:
        print(f"✅ Task reviewed: {args[0]}")
    else:
        print("❌ Failed to review task.")
        sys.exit(1)


def cmd_verifier_get(args):
    if not args:
        print("Usage: skill.py verifier-get <task_id>")
        return
    api = NexusAPI()
    result = api.get_verifier(args[0])
    if result:
        print(f"Verifier for {args[0]}: {result}")
    else:
        print("No verifier set.")


def cmd_verifier_set(args):
    if len(args) < 2:
        print("Usage: skill.py verifier-set <task_id> <verifier_agent_id>")
        return
    api = NexusAPI()
    result = api.set_verifier(args[0], args[1])
    if result:
        print(f"✅ Verifier set for {args[0]}: {args[1]}")
    else:
        print("❌ Failed to set verifier.")
        sys.exit(1)


def cmd_help(args):
    print("""
Reins (缰) — Entity CRUD & State Machine

Usage: python skill.py <command> [options]

Goal:
  goal-list [--status s]         List goals
  goal-create "title" [opts]     Create goal
  goal-update <id> [opts]        Update goal
  goal-delete <id>               Delete goal

Project:
  project-list [--goal-id id]    List projects
  project-create "name" --goal-id <id>  Create project
  project-update <id> [opts]     Update project
  project-delete <id>            Delete project

Task:
  task-list [--project-id id] [--goal-id id] [--status s]  List tasks
  task-create "title" --project-id <id>     Create task
  task-update <id> [opts]                   Update task
  task-complete <id> [--result r]           Complete task
  task-retry <id>                           Retry failed task
  task-fail <id> --error_message 'msg'      Report failure
  task-review <id> --action approve|reject  Human review
  task-delete <id>                          Delete task

Verifier:
  verifier-get <task_id>                    Get effective verifier
  verifier-set <task_id> <agent_id>         Set verifier

Options: --description "text" --priority high|medium|low --due-date "date" --category "cat"
         --status created|active|in_progress|completed|archived

Environment variables:
  NEXUS_SERVER_URL   Nexus API base (default: http://localhost:8090)
""")


COMMANDS = {
    "goal-list": cmd_goal_list, "goal-create": cmd_goal_create,
    "goal-update": cmd_goal_update, "goal-delete": cmd_goal_delete,
    "project-list": cmd_project_list, "project-create": cmd_project_create,
    "project-update": cmd_project_update, "project-delete": cmd_project_delete,
    "task-list": cmd_task_list, "task-create": cmd_task_create,
    "task-update": cmd_task_update, "task-complete": cmd_task_complete,
    "task-retry": cmd_task_retry, "task-fail": cmd_task_fail,
    "task-review": cmd_task_review, "task-delete": cmd_task_delete,
    "verifier-get": cmd_verifier_get, "verifier-set": cmd_verifier_set,
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
