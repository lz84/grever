# Sprint 46: 业务流修复 & 派发机制完善

**日期**: 2026-04-28
**负责人**: 扣子（开发）+ 刚子（审查）
**模型**: zhzy/qwen3-30b-a3b-fp8
**前置条件**: 后端 + 前端运行中，数据库可访问

---

## Sprint 目标

修复 2026-04-28 业务流审计发现的 5 个核心问题，确保：
1. 任务依赖正常工作（DAG 调度可用）
2. 任务可被 Agent 自动领取并执行
3. 数据干净（清理 orphan data）

---

## Task 分解

### Task 46-1: 修复任务依赖引用（P0，对应 Issue #22）

**目标**：将 `tasks.dependencies` JSON 中的 DAG 节点 ID（n1/n2/n3）映射为实际 task ID，并写入 `task_dependencies` 表。

**步骤**：
1. 遍历所有 tasks，解析 `dependencies` JSON 字段
2. 对每个 task，找到其所属 project → goal → workflow
3. 从 workflow 获取 DAG 数据，建立 `node_id → task_id` 映射
4. 替换 dependencies 中的 DAG 节点 ID 为实际 task ID
5. 写入 `task_dependencies` 表（规范化存储）
6. 无法映射的引用标记为 orphan 并清理

**验收标准**：
- `task_dependencies` 表有正确的外键引用
- 所有 task 的 dependencies JSON 引用有效的 task ID
- 无 orphan 引用
- 运行验证脚本无报错

**涉及文件**：
- 新文件：`scripts/fix_task_dependencies.py`
- 修改：`api/workflow_split.py`（修复映射逻辑，防止新数据继续损坏）

---

### Task 46-2: 心跳派发闭环（P1，对应 Issue #23a）

**目标**：Agent 心跳拉取任务时，自动更新任务状态为 in_progress。

**步骤**：
1. 修改 `POST /agents/{agent_id}/heartbeat` 端点
2. 分配任务给 agent 时，同步更新：
   - `status` → `in_progress`
   - `started_at` → 当前时间
   - `assigned_agent` → agent_id
3. 确保事务一致性（分配 + 状态更新一起提交）

**验收标准**：
- Agent 心跳后，返回的任务状态变为 in_progress
- 54 个 todo 任务可被正常领取
- 心跳端点 curl 验证通过

**涉及文件**：
- 修改：`api/assignment.py`

---

### Task 46-3: 后台任务调度器（P1，对应 Issue #23b）

**目标**：添加后台定时任务，自动将 todo 任务派发给可用 agent。

**步骤**：
1. 新建 `reins/services/task_dispatcher.py`
2. 实现 `dispatch_pending_tasks()` 函数：
   - 查询 `status=todo` 且 `assigned_agent IS NULL` 的任务
   - 调用 `agent_matcher` 找到最佳 agent（能力匹配 + 负载最低）
   - 更新 `assigned_agent`
3. 复用 `background_tasks.py` 的框架，添加定时循环
4. 在 `api/server.py` 的 lifespan 中启动调度器

**验收标准**：
- 后台调度器每 30 秒运行一次
- 新创建的 todo 任务在 30 秒内被分配给 agent
- 调度器日志清晰（分配了哪些任务、给哪个 agent）

**涉及文件**：
- 新文件：`reins/services/task_dispatcher.py`
- 修改：`api/server.py`（启动时注册）
- 复用：`reins/background_tasks.py`

---

### Task 46-4: 清理 draft goals（P2，对应 Issue #25）

**目标**：清理 10 个有 workflow 但未 confirm 的 draft goals。

**步骤**：
1. 新建 `scripts/cleanup_draft_goals.py`
2. 查询 `status=draft` 且有 `workflow_id` 但无 projects/tasks 的 goals
3. 删除对应的 orphan workflows 和 workflow_steps
4. 删除这些 draft goals

**验收标准**：
- 脚本运行后，无 orphan draft goals
- 有实际数据的 draft goals 保留
- 数据库行数变化符合预期

**涉及文件**：
- 新文件：`scripts/cleanup_draft_goals.py`

---

### Task 46-5: 处理空 projects（P2，对应 Issue #26）

**目标**：处理 25 个没有 tasks 的 projects。

**步骤**：
1. 新建 `scripts/cleanup_empty_projects.py`
2. 查询没有 tasks 的 projects
3. 区分两种情况：
   - DAG 节点类型不是 execution/step → 修改 `workflow_split.py` 也创建 placeholder task
   - 确实不需要的空项目 → 删除

**验收标准**：
- 空 projects 数量减少
- 或所有空 projects 都有 placeholder task
- workflow_split 不再产生空项目

**涉及文件**：
- 新文件：`scripts/cleanup_empty_projects.py`
- 修改：`api/workflow_split.py`（可选）

---

### Task 46-6: 状态定义统一（P2，对应 Issue #24）

**目标**：统一 engine.py 和 API 层的状态定义。

**步骤**：
1. 选择 API 层的状态定义作为标准（`todo/in_progress/done/blocked/review_needed`）
2. 修改 `engine.py` 的 `TaskState` 枚举，使用相同值
3. 或添加转换器映射两者
4. 更新所有引用 `TaskState` 的地方

**验收标准**：
- engine.py 和 API 层使用相同的状态字符串
- 所有状态转换逻辑正常工作
- 无编译/运行错误

**涉及文件**：
- 修改：`reins/engine.py`
- 修改：`reins/state_machine.py`
- 修改：`reins/models/task.py`（如有需要）

---

## 执行顺序

```
Task 46-1 (依赖修复) → Task 46-2 (心跳闭环) → Task 46-3 (调度器)
         ↓
Task 46-4 (清理 draft) → Task 46-5 (空 projects)
         ↓
Task 46-6 (状态统一)  ← 可并行
```

**优先级**：46-1 → 46-2 → 46-3 → 46-4 → 46-5 → 46-6

---

## Done 标准

- ✅ 代码修改完成
- ✅ 数据库迁移脚本可执行
- ✅ curl 验证 API 端点正常
- ✅ 前端页面无报错
- ✅ 端到端流程跑通：创建 Goal → 匹配场景 → 确认 Split → 任务自动派发 → Agent 领取 → 完成 → 进度更新

---

## 风险点

1. **依赖修复可能影响已有数据**：需要备份数据库后再执行迁移
2. **状态统一可能破坏现有逻辑**：需要充分测试
3. **后台调度器可能与手动派发冲突**：需要设计互斥机制
