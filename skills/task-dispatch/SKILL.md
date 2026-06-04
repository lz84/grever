---
name: task-dispatch
description: Create and dispatch tasks on Nexus platform via REST API. Agents can create verification tasks, assign to specific agents, and manage task lifecycle.
tags: [task-management, dispatch, coordination, nexus, api]
---

# Task Dispatch

Create and dispatch tasks on Nexus platform via REST API. Any agent can use this skill to create verification tasks, assign work, and manage the task lifecycle.

## When to Activate

- You need to create a new task and assign it to an agent (including verifier tasks)
- You need to dispatch a review_needed task back to an executor
- You need to check task status, update task fields, or mark tasks complete
- You need to create tasks under a specific goal or project

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXUS_SERVER_URL` | No | `http://localhost:8090` | Nexus API base URL |

## API Endpoints

All endpoints are under `{NEXUS_SERVER_URL}/api/v1/`.

### Create Task

```
POST /tasks
Content-Type: application/json

{
  "title": "Task title",
  "description": "Detailed task description",
  "priority": "high|medium|low|critical",
  "category": "optional category tag",
  "project_id": "optional project ID",
  "goal_id": "optional goal ID",
  "assigned_agent": "optional agent ID to assign directly",
  "status": "todo|in_progress|review_needed|disputed|done",
  "acceptance_criteria": {"criteria": [...]},
  "doc_refs": ["path/to/doc.md#section"],
  "workspace_path": "D:/work/research/agents-nexus"
}
```

**Response**: Returns the created task object with auto-generated `id` (format: `task-<uuid>`) and `status: 201`.

### Get Task

```
GET /tasks/{task_id}
```

### List Tasks

```
GET /tasks
```

Query parameters: `status`, `project_id`, `goal_id`, `assigned_agent`, `priority`

### Update Task

```
PUT /tasks/{task_id}
Content-Type: application/json

{
  "status": "in_progress",
  "assigned_agent": "kouzi",
  "description": "Updated description"
}
```

### Delete Task

```
DELETE /tasks/{task_id}
```

### Complete Task

```
POST /tasks/{task_id}/complete
Content-Type: application/json

{
  "status": "done",
  "result": "Task result summary (max 1000 chars)",
  "context_md": "### 📝 执行摘要\n- 做了什么：...\n### 📂 变更文件\n- ...\n### ✅ 验证方法\n- ...\n### 🔗 相关资源\n- ...",
  "execution_log": {
    "agent_id": "kouzi",
    "success": true,
    "duration_ms": 120000
  }
}
```

**注意**：如果任务 `needs_verification=True`，`context_md` 是必填字段。为空时返回 400 错误。context_md 必须包含 4 个小节：执行摘要、变更文件、验证方法、相关资源。

### Fail Task

```
POST /tasks/{task_id}/fail
Content-Type: application/json

{
  "error_message": "What went wrong",
  "error_type": "timeout|execution_error|validation_failed"
}
```

### Retry Task

```
POST /tasks/{task_id}/retry
```

Resets task status to `todo` and clears error_message for re-dispatch.

### Review Task (Human Review)

```
POST /tasks/{task_id}/review
Content-Type: application/json

{
  "action": "approve|reject",
  "reason": "Optional reason for rejection"
}
```

### Submit Ruling (Disputed Tasks)

```
POST /tasks/{task_id}/ruling
Content-Type: application/json

{
  "ruling": "Human ruling decision",
  "action": "done|in_progress|verifying"
}
```

### Get Verifier

```
GET /tasks/{task_id}/verifier
```

Returns the effective verifier agent (3-level inheritance: Task → Project → Goal → default).

### Set Verifier

```
POST /tasks/{task_id}/verifier
Content-Type: application/json

{
  "verifier_agent_id": "kouzi"
}
```

### Get Verification History

```
GET /tasks/{task_id}/verifications
```

### Get Failure Log

```
GET /tasks/{task_id}/failure-log
```

### Report Progress

```
POST /tasks/{task_id}/progress
Content-Type: application/json

{
  "progress": 50,
  "message": "Working on implementation..."
}
```

## Common Usage Patterns

### Pattern 1: Create and Assign a Task

```bash
curl -X POST {NEXUS_SERVER_URL}/api/v1/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Implement user authentication",
    "description": "Add JWT-based auth to the API",
    "priority": "high",
    "assigned_agent": "kouzi",
    "status": "todo"
  }'
```

### Pattern 2: Create a Verification Task

```bash
curl -X POST {NEXUS_SERVER_URL}/api/v1/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Verify API endpoint implementation",
    "description": "Run acceptance criteria checks for the new endpoint",
    "priority": "high",
    "assigned_agent": "kouzi",
    "status": "todo",
    "acceptance_criteria": {
      "criteria": [
        {"type": "api", "endpoint": "http://localhost:8090/api/v1/human-review/stats", "desc": "Stats endpoint returns 200"},
        {"type": "compile", "desc": "TypeScript compiles without errors"}
      ]
    }
  }'
```

### Pattern 3: Redispatch a Failed Task

```bash
# Reset task for re-dispatch
curl -X POST {NEXUS_SERVER_URL}/api/v1/tasks/{task_id}/retry

# Or update directly to reassign
curl -X PUT {NEXUS_SERVER_URL}/api/v1/tasks/{task_id} \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "todo",
    "assigned_agent": "kouzi",
    "error_message": null
  }'
```

### Pattern 4: Complete a Task

```bash
curl -X POST {NEXUS_SERVER_URL}/api/v1/tasks/{task_id}/complete \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "done",
    "result": "Implementation complete. All tests pass.",
    "execution_log": {
      "agent_id": "kouzi",
      "success": true,
      "duration_ms": 300000
    }
  }'
```

### Pattern 5: List Pending Tasks

```bash
# List all todo tasks
curl {NEXUS_SERVER_URL}/api/v1/tasks?status=todo

# List tasks assigned to a specific agent
curl {NEXUS_SERVER_URL}/api/v1/tasks?assigned_agent=kouzi&status=todo

# List review_needed tasks
curl {NEXUS_SERVER_URL}/api/v1/tasks?status=review_needed
```

## Task Status Flow

```
todo → in_progress → done
                   ↘ review_needed → (agent fixes) → in_progress → done
                                 ↘ disputed → human ruling → done/in_progress/verifying
```

## Acceptance Criteria Types

When creating tasks with verification criteria, use these types:

| Type | Description | Parameters |
|------|-------------|------------|
| `compile` | TypeScript compilation check | None (runs `npx tsc --noEmit` in NEXUS_DIR) |
| `api` | HTTP endpoint check | `endpoint` (URL to check) |
| `page` | Web page check | `url` (URL to fetch) |
| `custom` | Custom script check | `script` (Python code to run) |

## Task Fields Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Task title |
| `description` | string | No | Detailed description |
| `priority` | string | No | `critical`, `high`, `medium`, `low` |
| `category` | string | No | Category tag (e.g., "backend", "frontend") |
| `status` | string | No | `todo`, `in_progress`, `review_needed`, `disputed`, `done`, `failed` |
| `assigned_agent` | string | No | Agent ID to assign directly |
| `project_id` | string | No | Parent project ID |
| `goal_id` | string | No | Parent goal ID |
| `acceptance_criteria` | object | No | Verification criteria |
| `doc_refs` | array | No | Documentation references |
| `context_md` | string | No* | 执行者上下文（4 个必填小节），needs_verification=True 时必填 |
| `workspace_path` | string | No | Working directory path |

*`context_md` 在任务完成时，如果 needs_verification=True 则必填。
