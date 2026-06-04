# Sprint 86: 统一任务上下文 + 三级 context_md 系统

> 日期: 2026-05-22
> 优先级: P0
> 设计文档: `docs/02-架构设计/22-three-tier-context-system.md`
> 核心理念: **三条派发路径统一 → 所有 agent 拿到相同的完整上下文**

---

## 一、问题背景

### 1.1 三条路径，三套 prompt，互不相关

```
路径 A（心跳拉取）: task_context_builder.build_task_execution_context()
  → 🎯目标 → 📁工程 → 📋任务 → 验收标准 → 附件 → 依赖 ✅ 完整

路径 B（调度器推送）: task_runner.build_task_prompt()
  → 📋任务 → 验收标准 → 验证Agent
  ❌ 没有目标！没有工程！没有附件！没有依赖！

路径 C（验证者派发）: TaskBuilder.build()
  → 验证任务 → 结果摘要 → 验收标准 → 输出格式
  ❌ 没有目标！没有工程！没有任务详情！没有附件！
```

### 1.2 影响

- 85c-2 死循环 50+ 条评论的根因：谷子（路径B）和蚊子（路径C）拿到的信息完全不同
- 每次改一个路径的 prompt，另外两个不同步
- 加新字段（如 context_md）要改三个地方

### 1.3 目标

1. **统一入口**：三条路径只调 `build_task_execution_context()`
2. **context_md 注入**：执行者写的施工记录自动出现在验证者的 prompt 里
3. **不再有三个独立的 prompt 构建函数**

---

## 二、Phase 依赖关系

```
Phase 86a (DB+ORM)
   ↓ 全部完成
Phase 86b (统一路径) ← 核心，解决三套 prompt 问题
   ↓ 全部完成
Phase 86c (context_md 注入构建器)
   ↓ 全部完成
Phase 86d (完成时写Context + 技能)  ═══════════════╗
   ↓ 全部完成                                   ║
Phase 86e (前端展示) ←──────────────────────────╝
```

**86e 只依赖 86b 中的 API 端点，可和 86c/86d 并行。**

---

## 三、迭代任务分解

### Sprint 86a: DB 迁移 + ORM 模型

#### Task 86a-1: DB 迁移（migration 031）

**依赖**: `depends_on=[]`

**内容**: `ALTER TABLE` 给 tasks/projects/goals 加 `context_md TEXT`

**文件**:
- `packages/server/src/reins/persistence/migrations/031_three_tier_context.sql`
- `packages/server/src/reins/persistence/migrations/031_three_tier_context.down.sql`

**Acceptance Criteria**:
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "python -m py_compile 迁移脚本无报错"},
  {"type": "api", "name": "后端可启动", "endpoint": "http://127.0.0.1:8097/api/v1/health", "desc": "后端启动正常，返回 200"},
  {"type": "custom", "name": "数据流验证", "desc": "PRAGMA table_info 三个表都有 context_md 列；现有数据 context_md 为 NULL；migration 不丢数据"}
]}
```

#### Task 86a-2: ORM 模型 + Pydantic schemas

**依赖**: `depends_on=["86a-1"]`

**内容**: ORM + Pydantic 新增 `context_md: Optional[str]`

**文件**:
- `packages/server/src/reins/models/task.py`
- `packages/server/src/reins/models/project.py`
- `packages/server/src/reins/models/goal.py`
- `packages/server/src/reins/api/task_models.py`
- `packages/server/src/reins/api/project_models.py`
- `packages/server/src/reins/api/goal_models.py`

**Acceptance Criteria**:
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "python -m py_compile 所有修改的模型文件无报错"},
  {"type": "api", "name": "API返回context_md", "endpoint": "http://127.0.0.1:8097/api/v1/tasks/{任意已有task_id}", "desc": "GET 返回 200 + JSON 包含 context_md 字段"},
  {"type": "custom", "name": "数据流验证", "desc": "PUT 更新 context_md → 再次 GET 读取值一致 → DB 中有值（写回闭环）"}
]}
```

---

### Sprint 86b: 统一派发路径（核心）

#### Task 86b-1: 调度器推送路径统一（task_runner → context_builder）

**依赖**: `depends_on=["86a-2"]`

**内容**:
- `task_runner.py` 的 `build_task_prompt()` 改为调用 `build_task_execution_context()`
- 传入 task dict，拿到完整三级上下文 + 统一 prompt
- 确保 ProjectExecutor 派发时，执行者拿到和心跳路径相同的完整 prompt

**文件**:
- `packages/server/src/reins/scheduler/task_runner.py` (修改 build_task_prompt)
- `packages/server/src/reins/scheduler/project_executor.py` (可能微调传参)

**Acceptance Criteria**:
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "python -m py_compile task_runner.py 无报错"},
  {"type": "api", "name": "后端可启动", "endpoint": "http://127.0.0.1:8097/api/v1/health", "desc": "后端启动正常"},
  {"type": "custom", "name": "业务流验证", "desc": "模拟 ProjectExecutor 派发任务 → 生成的 prompt 包含 🎯目标 + 📁工程 + 📋任务 + 附件 + 依赖（和心跳路径一致）"},
  {"type": "custom", "name": "数据流验证", "desc": "task_runner.build_task_prompt(task) 内部调用 build_task_execution_context() 并返回 ctx['prompt']"}
]}
```

#### Task 86b-2: 验证者派发路径统一（VerificationDispatcher → context_builder）

**依赖**: `depends_on=["86a-2"]`

**内容**:
- `VerificationDispatcher.dispatch()` 改为调用 `build_task_execution_context()`
- 传入 task_id + result_summary
- 构建的 prompt 包含：目标 + 工程 + 任务详情 + context_md（如果有） + 验收标准 + 执行者结果摘要
- 删除 `TaskBuilder.build()`（不再需要）

**文件**:
- `packages/server/src/reins/verifiers/agent_dispatcher.py` (修改 dispatch 方法)
- 可选删除 `TaskBuilder` 类

**Acceptance Criteria**:
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "python -m py_compile agent_dispatcher.py 无报错"},
  {"type": "api", "name": "后端可启动", "endpoint": "http://127.0.0.1:8097/api/v1/health", "desc": "后端启动正常"},
  {"type": "custom", "name": "业务流验证", "desc": "模拟 VerificationDispatcher 派发 → 生成的 prompt 包含 🎯目标 + 📁工程 + 📋任务 + 执行者结果摘要"},
  {"type": "custom", "name": "数据流验证", "desc": "dispatch() 内部调用 build_task_execution_context() 构建 prompt，不再使用 TaskBuilder"}
]}
```

---

### Sprint 86c: context_md 注入统一构建器

#### Task 86c-1: context_builder 读取 context_md

**依赖**: `depends_on=["86b-1"]`

**内容**:
- `build_task_execution_context()` 的 SQL 查询增加 `t.context_md`, `p.context_md`, `g.context_md`
- ctx dict 新增 `task.context_md`, `project.context_md`, `goal.context_md` 字段

**文件**:
- `packages/server/src/reins/scheduler/task_context_builder.py` (修改)

**Acceptance Criteria**:
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "python -m py_compile task_context_builder.py 无报错"},
  {"type": "api", "name": "后端可启动", "endpoint": "http://127.0.0.1:8097/api/v1/health", "desc": "后端启动正常"},
  {"type": "custom", "name": "数据流验证", "desc": "build_task_execution_context() 返回的 ctx 包含 task/project/goal 的 context_md 字段（有值或 null）"}
]}
```

#### Task 86c-2: context_builder 注入 context_md 到 prompt

**依赖**: `depends_on=["86c-1"]`

**内容**:
- `_build_unified_prompt()` 新增 `### 📝 执行者上下文` 小节
- 读取 task.context_md，如果非空则 Markdown 渲染到 prompt 中
- 验证者路径也能看到执行者写的 URL、文件变更、验证命令

**文件**:
- `packages/server/src/reins/scheduler/task_context_builder.py` (修改 _build_unified_prompt)

**Acceptance Criteria**:
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "python -m py_compile task_context_builder.py 无报错"},
  {"type": "custom", "name": "业务流验证", "desc": "给 task 写入 context_md → 构建 prompt → prompt 中包含 '### 📝 执行者上下文' + context_md 内容"},
  {"type": "custom", "name": "数据流验证", "desc": "context_md 为空时 prompt 不显示该小节；context_md 有值时完整渲染"}
]}
```

---

### Sprint 86d: 完成时写 Context + 技能固化

#### Task 86d-1: 完成时 context_md 校验

**依赖**: `depends_on=["86c-2"]`

**内容**: task complete 时检查 context_md，为空则拒绝

**文件**:
- `packages/server/src/reins/api/tasks_crud.py`

**Acceptance Criteria**:
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "python -m py_compile tasks_crud.py 无报错"},
  {"type": "api", "name": "完成时校验", "endpoint": "http://127.0.0.1:8097/api/v1/tasks/{id}/complete", "desc": "context_md 为空且 needs_verification=True → 400；有 context_md → 200"},
  {"type": "custom", "name": "数据流验证", "desc": "DB 中 task 的 context_md 有值，status 从 in_progress 变为 review_needed"}
]}
```

#### Task 86d-2: 执行者技能更新

**依赖**: `depends_on=["86c-2"]`

**内容**: 技能文件新增 context_md 填写规则 + 模板

**Acceptance Criteria**:
```json
{"criteria": [
  {"type": "custom", "name": "业务流验证", "desc": "技能文件中包含 context_md 填写规则（4 个必填小节）"},
  {"type": "custom", "name": "数据流验证", "desc": "模板格式可被 context_builder 正确解析"},
  {"type": "custom", "name": "页面流验证", "desc": "技能文件在技能展示页面中可预览"}
]}
```

#### Task 86d-3: Project context 自动汇总

**依赖**: `depends_on=["86c-2"]`

**内容**: Project 下任务全完成时自动汇总子任务 context_md

**文件**:
- `packages/server/src/reins/scheduler/project_context_aggregator.py` (新建)

**Acceptance Criteria**:
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "python -m py_compile 无报错"},
  {"type": "custom", "name": "业务流验证", "desc": "Project 下 task 全 done → project.context_md 自动填充"},
  {"type": "custom", "name": "数据流验证", "desc": "汇总格式正确，子任务 context 不丢失且标记来源"}
]}
```

---

### Sprint 86e: 前端 Context 展示

#### Task 86e-1: Context API 端点

**依赖**: `depends_on=["86a-2"]`

**内容**: 6 个端点 — GET/PUT `/tasks|projects|goals/{id}/context`

**文件**:
- `packages/server/src/reins/api/context_routes.py` (新建)
- `packages/server/src/reins/api/context_models.py` (新建)
- `packages/server/src/reins/api/server.py` (注册)

**Acceptance Criteria**:
```json
{"criteria": [
  {"type": "compile", "name": "Python编译", "desc": "python -m py_compile 无报错"},
  {"type": "api", "name": "6个端点可用", "endpoint": "http://127.0.0.1:8097/api/v1/tasks/{id}/context", "desc": "GET/PUT 返回 200，不存在返回 404"},
  {"type": "custom", "name": "数据流验证", "desc": "PUT → DB 更新 → GET 返回相同值；三级各验证一遍"}
]}
```

#### Task 86e-2: Task Detail 新增 Context Tab

**依赖**: `depends_on=["86e-1"]`

**内容**: Task Detail 新增 Context Tab，Markdown 渲染 + 编辑

**文件**:
- `packages/ui/src/pages/TaskDetail.tsx`
- `packages/ui/src/components/ContextViewer.tsx` (新建)
- `packages/ui/src/components/ContextEditor.tsx` (新建)

**Acceptance Criteria**:
```json
{"criteria": [
  {"type": "compile", "name": "TypeScript编译", "desc": "npx tsc --noEmit 0 errors"},
  {"type": "api", "name": "Context API调用", "endpoint": "http://127.0.0.1:8097/api/v1/tasks/{id}/context", "desc": "GET/PUT 均返回 200"},
  {"type": "page", "name": "页面渲染", "url": "http://localhost:5173/tasks/{id}", "desc": "Context Tab 显示，Markdown 渲染正确"},
  {"type": "custom", "name": "数据流验证", "desc": "编辑后保存 → 刷新不丢失；DB 与前端一致"}
]}
```

#### Task 86e-3: Project/Goal Detail 新增 Context Tab

**依赖**: `depends_on=["86e-1"]`

**内容**: Project Detail 和 Goal Detail 新增 Context Tab

**文件**:
- `packages/ui/src/pages/ProjectDetail.tsx`
- `packages/ui/src/pages/GoalDetail.tsx`

**Acceptance Criteria**:
```json
{"criteria": [
  {"type": "compile", "name": "TypeScript编译", "desc": "npx tsc --noEmit 0 errors"},
  {"type": "api", "name": "Context API调用", "endpoint": "http://127.0.0.1:8097/api/v1/projects/{id}/context", "desc": "两个页面分别调用 GET，返回 200"},
  {"type": "page", "name": "ProjectDetail渲染", "url": "http://localhost:5173/projects/{id}", "desc": "Context Tab 正常显示"},
  {"type": "page", "name": "GoalDetail渲染", "url": "http://localhost:5173/goals/{id}", "desc": "Context Tab 正常显示"},
  {"type": "custom", "name": "数据流验证", "desc": "三个页面数据来自对应 DB 字段，不串数据"}
]}
```

---

## 四、完整依赖关系图

```
86a-1 (DB 迁移)
   ↓
86a-2 (ORM + Pydantic)
   ├──────────────┐
   ↓              ↓
86b-1 (调度器统一)  86b-2 (验证者统一)
   ↓              ↓
86c-1 (读取context_md) ← 依赖 86b-1
   ↓
86c-2 (注入prompt)
   ↓
86d-1 (完成时校验)
   ↓
86d-2 (技能更新)

86d-3 (Project 汇总) ← 依赖 86c-2

86e-1 (Context API) ← 依赖 86a-2
   ↓
86e-2 (Task Detail)   86e-3 (Project/Goal Detail)
```

---

## 五、验收三板斧总览

| 任务 | 编译 | API/业务流 | 数据流 | 页面流 |
|------|------|-----------|--------|--------|
| 86a-1 | ✅ | ✅ 后端启动 | ✅ 列检查 | N/A |
| 86a-2 | ✅ | ✅ GET返回 | ✅ 写回闭环 | N/A |
| 86b-1 | ✅ | ✅ prompt完整 | ✅ 调用统一构建器 | N/A |
| 86b-2 | ✅ | ✅ prompt完整 | ✅ 调用统一构建器 | N/A |
| 86c-1 | ✅ | ✅ 后端启动 | ✅ context_md字段读取 | N/A |
| 86c-2 | ✅ | ✅ prompt含context | ✅ 空/有值两种情况 | N/A |
| 86d-1 | ✅ | ✅ 400/200 | ✅ 状态变更 | N/A |
| 86d-2 | N/A | ✅ 规则完整 | ✅ 模板可解析 | ✅ 技能页面 |
| 86d-3 | ✅ | ✅ 汇总触发 | ✅ 数据不丢失 | N/A |
| 86e-1 | ✅ | ✅ 6端点 | ✅ PUT→GET→DB | N/A |
| 86e-2 | ✅ TS | ✅ API调用 | ✅ 保存不丢失 | ✅ Tab渲染 |
| 86e-3 | ✅ TS | ✅ API调用 | ✅ 数据不串 | ✅ 两个页面 |

---

## 六、文件变更清单

### 新建
```
packages/server/src/reins/persistence/migrations/031_three_tier_context.sql + down.sql
packages/server/src/reins/api/context_routes.py
packages/server/src/reins/api/context_models.py
packages/server/src/reins/scheduler/project_context_aggregator.py
packages/ui/src/components/ContextViewer.tsx
packages/ui/src/components/ContextEditor.tsx
```

### 修改
```
packages/server/src/reins/models/task.py / project.py / goal.py
packages/server/src/reins/api/task_models.py / project_models.py / goal_models.py
packages/server/src/reins/scheduler/task_context_builder.py (核心修改)
packages/server/src/reins/scheduler/task_runner.py (删除 build_task_prompt，改用统一构建器)
packages/server/src/reins/scheduler/project_executor.py (微调传参)
packages/server/src/reins/verifiers/agent_dispatcher.py (改用统一构建器)
packages/server/src/reins/api/tasks_crud.py (完成时校验)
packages/server/src/reins/api/server.py (注册路由)
skills/reins/SKILL.md (新增规则)
packages/ui/src/pages/TaskDetail.tsx / ProjectDetail.tsx / GoalDetail.tsx
```
