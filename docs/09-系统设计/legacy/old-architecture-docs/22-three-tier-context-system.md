# 三级上下文文档系统设计

> Sprint 86 设计文档
> 创建时间：2026-05-21
> 状态：待实现

## 1. 问题描述

### Sprint 85 暴露的问题

谷子（执行者）完成了 85c-2 和 85d-1 的代码，知道：
- 前端 URL 是 `localhost:5173/scenarios`
- API endpoint 是 `http://127.0.0.1:8097/api/v1/scenarios/`
- 改了哪些文件

但蚊子（验证者）收到验证任务时：
- 不知道 URL 是什么
- 不知道改了什么文件
- 不知道需要重启 Vite 才能看到变化

验收条件里只写了自然语言描述（"ScenarioList显示project_count"），没有 URL。
结果：验证失败 → disputed → 反复循环。

### 根因

**上下文信息在执行者完成时产生，但没有传递给验证者。**

不是"验收条件没写对"的问题，而是**信息传递链路断裂**：
```
执行者完成 → 产生上下文（URL、文件、命令）→ ??? → 验证者拿到上下文 → 验证
                                         ↑ 这里断了
```

## 2. 设计方案

### 2.1 三级 Context 文档

每个 Goal / Project / Task 都有自己的 `context_md` 字段（DB TEXT 存储）：

| 级别 | 字段 | 内容 | 填写时机 |
|------|------|------|----------|
| **Goal** | `goals.context_md` | 目标描述、环境信息、相关系统地址、工作目录 | Goal 创建时 |
| **Project** | `projects.context_md` | 部署地址、API endpoint、验证 URL、文件变更清单 | Project 激活时 |
| **Task** | `tasks.context_md` | 修改的文件、测试命令、已知问题、验证步骤 | 任务完成时 |

### 2.2 信息传递流程

```
执行者完成 Task
    ↓
更新 task.context_md（写入 URL、文件、命令）
    ↓
标记 task status = done
    ↓
触发 Project context_md 更新（汇总所有子任务信息）
    ↓
验证者开始验证
    ↓
读取 task.context_md + project.context_md
    ↓
获取验证所需全部上下文 → 执行验证
```

### 2.3 评论系统（补充）

每个 Task 已有 `task_comments` 表，用于实时双向沟通：

- 执行者留言："代码已提交，前端在 localhost:5173/scenarios"
- 验证者提问："这个 endpoint 的完整 URL 是什么？"
- 执行者回复："http://127.0.0.1:8097/api/v1/scenarios/{id}/fullset"

**评论 vs Context 的区别：**
- 评论 = 实时对话，适合讨论、提问、回复
- Context = 结构化沉淀，适合验证者快速获取信息

## 3. Context 文档格式

### Task Context 模板

```markdown
# Task Context: {task_title}

## 基本信息
- ID: {task_id}
- 执行者: {agent_name} ({agent_id})
- 完成时间: {timestamp}
- Project: {project_name}

## 修改内容
### 文件变更
- `packages/ui/src/pages/ScenarioList.tsx` — 新增"项目数"和"能力标签"两列
- `packages/ui/src/utils/scenariosApi.ts` — Scenario 接口新增字段

### Git Commit
- abc1234: feat: add project_count to ScenarioList

## 验证信息
### URL
- 前端: http://localhost:5173/scenarios
- API: http://127.0.0.1:8097/api/v1/scenarios/

### 验证命令
```bash
# API 验证
curl http://127.0.0.1:8097/api/v1/scenarios/ | jq '.[0].project_count'

# TS 编译
cd packages/ui && npx tsc --noEmit
```

### 前置条件
- 前端需要重启 Vite 才能看到变化
- 后端已重启（端口 8097）

### 注意事项
- project_count 字段在场景无项目时返回 0
- goal_capability_tags 是对象格式，不是数组

## 已知问题
- 暂无
```

### Project Context 模板

```markdown
# Project Context: {project_name}

## 基本信息
- ID: {project_id}
- Goal: {goal_title}
- 状态: {status}
- 依赖: {depends_on}

## 部署信息
- 前端: http://localhost:5173
- 后端: http://127.0.0.1:8097
- 数据库: D:\work\research\agents-nexus\data\reins.db

## 子任务汇总
| Task | 状态 | 修改文件 | 验证 URL |
|------|------|----------|----------|
| 85c-1 | done | GoalDetail.tsx | http://localhost:5173/goals/xxx |
| 85c-2 | done | ScenarioList.tsx | http://localhost:5173/scenarios |

## 文件变更总览
- `packages/ui/src/pages/GoalDetail.tsx`
- `packages/ui/src/pages/ScenarioList.tsx`
- `packages/ui/src/utils/scenariosApi.ts`
- `packages/server/src/reins/api/scenarios_crud.py`
```

### Goal Context 模板

```markdown
# Goal Context: {goal_title}

## 基本信息
- ID: {goal_id}
- 模式: {mode}
- 状态: {status}
- 场景: {scenario_name}

## 环境信息
- Nexus Base URL: http://127.0.0.1:8097
- 前端地址: http://localhost:5173
- 工作目录: D:\work\research\agents-nexus

## 子 Project
| Project | 状态 | 依赖 | 验证 URL |
|---------|------|------|----------|
| 85a-DB结构重构 | done | - | - |
| 85b-API层重构 | done | 85a | http://127.0.0.1:8097/api/v1/scenarios/ |
| 85c-前端重构 | done | 85b | http://localhost:5173/scenarios |
| 85d-实例化入口 | done | 85c | http://localhost:5173/scenarios/{id} |
| 85e-全量测试 | in_progress | 85a,85b,85c,85d | - |
```

## 4. 实现步骤

### Phase 1: DB 迁移 + API

1. **DB 迁移**（migration 031）
   ```sql
   ALTER TABLE tasks ADD COLUMN context_md TEXT;
   ALTER TABLE projects ADD COLUMN context_md TEXT;
   ALTER TABLE goals ADD COLUMN context_md TEXT;
   ```

2. **API 端点**
   ```
   GET    /api/v1/tasks/{id}/context      # 读取 task context
   PUT    /api/v1/tasks/{id}/context      # 更新 task context
   GET    /api/v1/projects/{id}/context   # 读取 project context
   PUT    /api/v1/projects/{id}/context   # 更新 project context
   GET    /api/v1/goals/{id}/context      # 读取 goal context
   PUT    /api/v1/goals/{id}/context      # 更新 goal context
   ```

3. **Pydantic 模型**
   ```python
   class ContextUpdate(BaseModel):
       context_md: str
   ```

### Phase 2: 验证流程集成

1. **验证者自动读取 context**
   - 验证流程开始时，自动读取 task.context_md
   - 从 context_md 中提取 URL 注入到验证条件
   - 如果 context_md 为空，返回 "缺少上下文，无法验证"

2. **context 注入验证条件**
   ```python
   # 验证者读取 context_md
   context_md = task.context_md or ""
   # 提取 URL
   urls = extract_urls(context_md)
   # 注入到验证条件
   for criterion in acceptance_criteria:
       if criterion.type == "page" and not criterion.url:
           criterion.url = urls.get("frontend")
   ```

### Phase 3: 任务完成时自动写 context

1. **执行者完成时提示填写**
   - 任务标记 done 时，检查 context_md 是否为空
   - 为空 → 在任务描述中提示执行者填写
   - 或从 git diff 自动生成部分内容

2. **Project context 自动汇总**
   - 当 Project 下所有任务都完成时
   - 自动汇总所有子任务的 context_md 到 Project context_md

### Phase 4: 前端展示

1. **Task Detail 页面**
   - 新增 "Context" tab
   - Markdown 渲染 context_md
   - 编辑按钮（执行者可更新）

2. **Project Detail 页面**
   - 新增 "Context" tab
   - 显示部署信息、文件变更总览

3. **Goal Detail 页面**
   - 新增 "Context" tab
   - 显示环境信息、子 Project 汇总

## 5. 与现有系统的关系

| 现有模块 | 关系 |
|----------|------|
| `task_context_builder.py` | 已有三级上下文读取（DB 字段），扩展为同时读取 context_md |
| `task_comments` 表 | 评论系统已存在，context_md 是补充 |
| `attachments` 系统 | 附件可作为 context 的补充 |
| `workspace_path` 字段 | Task 已有 workspace_path，context_md 是结构化信息 |

## 6. 风险与注意事项

1. **context_md 为空时的降级**
   - 如果执行者没写 context_md，验证者应该能 fallback 到现有逻辑
   - 但应该在任务描述中强制要求填写

2. **context_md 的格式规范**
   - 需要约定 Markdown 格式
   - URL 应该有固定格式，方便自动提取

3. **安全性**
   - context_md 可能包含敏感信息（token、密码）
   - 需要脱敏处理
