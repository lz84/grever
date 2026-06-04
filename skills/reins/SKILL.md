---
name: reins
description: 对目标、项目、任务进行增删改查，支持状态机流转、验证者设置和任务重试。是 Nexus 平台的核心管理接口。
tags: [coordination, crud, state-machine, entity-management, nexus]
---

# reins

目标/项目/任务 CRUD — 增删改查和状态机流转。

## 何时激活

- 需要创建/更新/删除目标、项目、任务
- 需要查询列表（按状态/目标/项目筛选）
- 需要更新任务状态（todo → in_progress → done）
- 需要设置验证者或更新任务字段

## 配置

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `NEXUS_SERVER_URL` | 否 | `http://localhost:8090` | Nexus API 地址 |

## Goal CRUD

### 创建

```bash
POST {NEXUS_SERVER_URL}/api/v1/goals
{
  "title": "...",
  "description": "...",
  "priority": "high|medium|low",
  "status": "active"
}
```

### 列表

```bash
GET {NEXUS_SERVER_URL}/api/v1/goals
GET {NEXUS_SERVER_URL}/api/v1/goals?status=active
```

### 更新

```bash
PUT {NEXUS_SERVER_URL}/api/v1/goals/{id}
{
  "status": "in_progress",
  "progress": 50
}
```

### 删除

```bash
DELETE {NEXUS_SERVER_URL}/api/v1/goals/{id}
```

## Project CRUD

```bash
GET/POST/PUT/DELETE /api/v1/projects
```

## Task CRUD

```bash
GET/POST/PUT/DELETE /api/v1/tasks
```

### 完成任务

```bash
POST {NEXUS_SERVER_URL}/api/v1/tasks/{id}/complete
{
  "result": "任务完成摘要"
}
```

## 状态机

```
Goal:    created → active → completed → archived
Project: created → active → in_progress → completed → archived
Task:    todo → in_progress → done
                            ↘ review_needed → (修复) → in_progress
                                       ↘ disputed → 人工裁决
```

## context_md 填写规则（Sprint 86）

### 三条铁律

1. **执行时必须写 context_md**：任何任务从 `in_progress` 完成时（status → `done`/`review_needed`），必须填写 `context_md`。空 context_md + `needs_verification=True` → 任务拒绝完成（400 错误）。
2. **四级必填结构**：context_md 必须包含以下 4 个小节，缺一不可：

```markdown
### 📝 执行摘要
- 做了什么：[简述核心改动]
- 关键决策：[重要选择及原因]
- 已知风险：[遗留问题或注意事项]

### 📂 变更文件
- `packages/server/src/reins/api/tasks_crud.py` — 修改了任务完成时的 context_md 校验逻辑
- `packages/ui/src/pages/TaskDetail.tsx` — 新增 Context Tab 组件

### ✅ 验证方法
- `curl http://127.0.0.1:8097/api/v1/tasks/{id}/complete` — 返回 200
- `python -m py_compile tasks_crud.py` — 无报错
- DB 中 task.context_md 有值，status 变为 review_needed

### 🔗 相关资源
- 设计文档：`docs/sprint-86-context.md`
- 相关 PR：#123
- 前置任务：`task-xxx` 已完成
```

3. **验证者能看到执行者上下文**：验证者派发路径的 prompt 会自动注入 `### 🧭 执行者上下文` 小节，包含上述完整 context_md。验证者据此判断工作是否达标。

### context_md 写入端点

```bash
# 方式 A：完成任务时附带
POST {NEXUS_SERVER_URL}/api/v1/tasks/{id}/complete
{
  "result": "任务完成摘要",
  "context_md": "### 📝 执行摘要\n...\n### 🔗 相关资源\n..."
}

# 方式 B：单独更新
PUT {NEXUS_SERVER_URL}/api/v1/tasks/{id}/context
{
  "context_md": "### 📝 执行摘要\n...\n### 🔗 相关资源\n..."
}

# 方式 C：通过普通 PUT
PUT {NEXUS_SERVER_URL}/api/v1/tasks/{id}
{
  "status": "done",
  "context_md": "### 📝 执行摘要\n..."
}
```

### Project/Goal 级别的 context_md

- **Project context_md**：当 Project 下所有 Task 完成时，自动汇总子任务的 context_md 为 Project 级摘要。也可手动填写。
- **Goal context_md**：当 Goal 下所有 Project 完成时，自动汇总。也可手动填写。

### 上下文读取端点

```bash
# 读取任意级别的 context_md
GET {NEXUS_SERVER_URL}/api/v1/tasks/{id}/context
GET {NEXUS_SERVER_URL}/api/v1/projects/{id}/context
GET {NEXUS_SERVER_URL}/api/v1/goals/{id}/context
```

## 与其他技能的关系

- **目标分解**: 分解生成 Project/Task 树，reins 对树进行日常管理
- **生命周期**: reins 不处理智能体注册/心跳，这些由生命周期技能负责
- **执行引擎**: 执行引擎通过 reins 的 CRUD 更新任务状态和上报结果
- **统一验证**: 验证器通过 reins 的 CRUD 更新验证结果和任务状态
