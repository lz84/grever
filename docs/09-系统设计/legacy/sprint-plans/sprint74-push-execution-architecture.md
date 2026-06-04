# Sprint 74: Nexus 主动推送执行架构

> **核心思想**：Nexus 从"被动等待 Worker 心跳"变成"主动驱动 OpenClaw 执行任务"

## 架构变更

### 现在（Pull 模式）
```
Worker 进程 (需常驻) ──心跳──→ Nexus 领任务 ──执行──→ 上报结果
      ↑ 死了没人管，经常断
```

### 改后（Push 模式）
```
Nexus tick(30s)
  └── 遍历活跃项目 (active/in_progress)
       └── Project Executor (每个项目一个 asyncio 协程)
            ├── 找 ready 任务（依赖全 done）
            ├── 触发新任务（调 OpenClaw CLI，非阻塞）
            ├── poll in_progress 池（收集完成的）
            ├── 完成 → 写结果 → 验证 → 解锁下游
            └── in_progress 为空 且 无 ready → 项目完成
```

## 关键设计原则

1. **项目级隔离**：每个项目独立执行，互不阻塞
2. **DAG 驱动并发**：依赖图决定并行度，调度器不决策
3. **非阻塞执行**：启动任务后继续判断，不傻等
4. **状态在 Nexus**：不再依赖 Agent 本地内存
5. **砍掉 Worker**：`agent_worker.py` 不再需要

## 新增文件

| 文件 | 职责 |
|------|------|
| `scheduler/project_executor.py` | 单项目执行逻辑：找 ready 任务、触发、poll、收集结果 |
| `scheduler/task_runner.py` | 调 OpenClaw CLI 执行单个任务，管理 subprocess |

## 修改文件

| 文件 | 改动 |
|------|------|
| `scheduler/core.py` | 新增 `project_executors` 管理，Step 5 改为启动项目执行器 |
| `api/tasks.py` | 创建任务时 `project_id` 必填（新增约束） |
| `migration/019_project_constraint.py` | `tasks.project_id NOT NULL` 约束 |

## 执行流程（单项目）

```python
# ProjectExecutor._tick():

# 1. poll 已启动的任务
for task_id, process in self.in_progress.items():
    if process.poll() is not None:
        completed.append(task_id)

# 2. 处理完成的：读结果 → 调 complete_task API → 触发验证
for task_id in completed:
    result = read_result_file(task_id)
    complete_task(task_id, result)
    verifier.trigger_verification(task_id, result)
    # dependency_resolver 自动解锁下游

# 3. 找新的 ready 任务
ready_tasks = find_tasks_where(
    status='todo',
    project_id=self.project_id,
    all_dependencies_done=True
)

# 4. 触发新任务（非阻塞）
for task in ready_tasks:
    process = task_runner.launch(task)
    self.in_progress[task_id] = process

# 5. 判断是否完成
if not self.in_progress and not ready_tasks:
    self.state = 'completed'
```

## 不影响的组件

- `result_verifier.py` — 验证逻辑不变
- `dependency_resolver.py` — 解锁逻辑不变
- `health_manager.py` — 心跳扫描不变
- 前端 API — 任务状态流转不变
- 数据库表结构 — 只加约束，不改 schema

## 迁移步骤

1. 新增 `019_project_constraint.py`：无 project 的任务挂到 "Nexus 内部" 项目
2. 新增 `project_executor.py` + `task_runner.py`
3. 改 `core.py`：Step 5 启用项目执行器
4. 验证：创建测试项目 + 任务，确认端到端跑通
5. 废弃 `agent_worker.py`

## Acceptance Criteria

{"criteria": [
  {"type": "api", "name": "项目创建后自动触发", "endpoint": "POST /api/v1/projects", "desc": "创建项目后，scheduler tick 自动启动 executor"},
  {"type": "api", "name": "任务完成验证", "desc": "in_progress → done，验证流程触发，下游任务解锁"},
  {"type": "custom", "name": "并发执行", "desc": "无依赖的任务同时触发 OpenClaw CLI，不是串行"},
  {"type": "custom", "name": "无 Worker 进程", "desc": "不依赖 agent_worker.py 也能完成任务派发执行"},
  {"type": "compile", "name": "TypeScript 编译", "desc": "npx tsc --noEmit 0 errors"},
  {"type": "compile", "name": "Python 编译", "desc": "python -m py_compile 通过"}
]}
