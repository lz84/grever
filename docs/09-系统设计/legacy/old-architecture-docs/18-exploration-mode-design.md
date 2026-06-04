# 探索模式：方案执行链设计

> **日期**：2026-05-14
> **触发根因**：当前探索模式只展示方案名称+评分，方案背后的执行链（工程/任务/流程）完全不透明
> **核心原则**：找到最优解 ≠ 复制最优解。必须两者兼顾。

---

## 一、问题定义

### 现状：方案黑盒

当前探索模式的"方案对比"卡片：

```
┌──────────────┬──────────────┬──────────────┐
│  方案A       │  方案B ⭐    │  方案C       │
│  综合评分 0.82 │  综合评分 0.91 │  综合评分 0.78 │
└──────────────┴──────────────┴──────────────┘
```

用户看到方案B最优，但不知道：
- 方案B用了哪些工程？（proj-001, proj-002）
- 方案B有哪些任务？（task-101, task-102, ...）
- 方案B的流程是什么？（场景A → 场景B → 场景C）
- 方案B的约束参数是什么？（工期≤7天，成本≤¥300）

**结果**：用户选了一个"最优解"，但不知道怎么复制它。

### 目标：方案执行链透明

每个方案必须附带完整的执行蓝图：

```
┌─────────────────────────────────────────────────┐
│ 🎯 方案B（最优）  综合评分 0.91                 │
├─────────────────────────────────────────────────┤
│ 📊 维度评分                                    │
│ 工期 78%  成本 95%  安全 88%                 │
├─────────────────────────────────────────────────┤
│ ⚙️ 约束参数                                    │
│ 工期≤7天 | 成本≤¥300 | 安全系数≥1.5          │
├─────────────────────────────────────────────────┤
│ 🏗️ 执行工程 (3个)                             │
│ ├── 工程A：场景适配（proj-001）                 │
│ ├── 工程B：资源调度（proj-002）                 │
│ └── 工程C：安全保障（proj-003）                 │
├─────────────────────────────────────────────────┤
│ 📋 任务列表 (7个)                              │
│ ├── task-101: 场景勘测 [已完成]                │
│ ├── task-102: 资源调配 [已完成]                │
│ ├── task-103: 方案制定 [已完成]                │
│ └── ...                                        │
├─────────────────────────────────────────────────┤
│ 🔀 流程路径                                    │
│ 场景A → 场景B → 场景C                         │
├─────────────────────────────────────────────────┤
│ 💾 [复制此方案]  ← 点击可创建新目标            │
└─────────────────────────────────────────────────┘
```

---

## 二、为什么方案必须透明

### 核心价值：复制最优解

探索模式的本质是**实验+选择**：

```
探索模式 = 做实验（生成方案） → 看结果（评分对比） → 选最优 → 复制执行
                         ↑ 这里是当前做的
                              ↑ 这里完全缺失
```

如果方案不透明：
1. 找到了最优方案B（评分0.91）
2. 但不知道B怎么做的（用了哪些工程/任务/流程）
3. 没法在另一个目标里复制B的执行方式
4. 探索的结果无法落地

**只有方案透明，才能真正发挥探索模式的价值。**

### 探索模式的完整价值链

```
┌──────────────────────────────────────────────────────┐
│                 探索模式完整价值链                      │
│                                                       │
│  探索 → 找到最优解 → 理解最优解 → 复制最优解         │
│    ↑          ↑               ↑            ↑         │
│  当前有    当前有           新增需求      新增需求     │
│                                                       │
└──────────────────────────────────────────────────────┘
```

---

## 三、数据模型扩展

### solutions 表必须包含执行链

每个 solution 记录应该包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | 方案ID |
| goal_id | TEXT FK | 目标ID |
| name | TEXT | 方案名称 |
| score | REAL | 综合评分 |
| status | TEXT | optimal/compliant/non_compliant/rejected/pending |
| round | INT | 第几轮生成 |
| **project_ids** | TEXT (JSON) | 关联的工程ID列表 `["proj-001", "proj-002"]` |
| **task_ids** | TEXT (JSON) | 关联的任务ID列表 `["task-101", "task-102"]` |
| **workflow_id** | TEXT FK | 使用的场景/工作流ID |
| **parameters** | TEXT (JSON) | 方案参数 `{duration: 7, cost: 300, safety: 1.5}` |
| **dimensions** | TEXT (JSON) | 维度评分 `{duration: 78, cost: 95, safety: 88}` |
| **execution_summary** | TEXT | 执行摘要（AI生成） |

### 方案详情 API 响应

```json
{
  "id": "sol-xxx",
  "name": "方案B-综合最优",
  "goal_id": "goal-xxx",
  "round": 2,
  "score": 0.91,
  "status": "optimal",
  "parameters": {
    "duration": 7,
    "cost": 300,
    "safety": 1.5
  },
  "dimensions": {
    "duration": 78,
    "cost": 95,
    "safety": 88
  },
  "execution_chain": {
    "projects": [
      {"id": "proj-001", "name": "工程A：场景适配", "status": "completed"},
      {"id": "proj-002", "name": "工程B：资源调度", "status": "completed"},
      {"id": "proj-003", "name": "工程C：安全保障", "status": "completed"}
    ],
    "tasks": [
      {"id": "task-101", "title": "场景勘测", "status": "done", "assigned_agent": "mazi"},
      {"id": "task-102", "title": "资源调配", "status": "done", "assigned_agent": "guzi"},
      {"id": "task-103", "title": "方案制定", "status": "done", "assigned_agent": "gangzi"}
    ],
    "workflow": {
      "id": "wf-xxx",
      "name": "化工园区应急处置",
      "steps": [
        {"name": "启动应急响应", "status": "done"},
        {"name": "泄漏源控制", "status": "done"},
        {"name": "警戒与疏散", "status": "done"},
        {"name": "环境监测", "status": "done"}
      ]
    }
  },
  "execution_summary": "本方案采用快速响应策略，通过多工程并行推进，在7天内完成应急处置，成本控制在¥300以内，安全系数达到1.8。",
  "created_at": "2026-05-14T10:00:00Z"
}
```

---

## 四、页面设计

### 方案详情面板（探索模式）

点击方案对比卡片中的某个方案，展开详情：

```
┌─────────────────────────────────────────────────────────┐
│  方案详情: 方案B-综合最优                          [×] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ⭐ 最优方案  |  综合评分 0.91  |  第2轮生成           │
│                                                         │
│  ── 维度评分 ──────────────────────────────────────     │
│  工期  ▓▓▓▓▓▓▓▓░░ 78%                               │
│  成本  ▓▓▓▓▓▓▓▓▓▓ 95%                              │
│  安全  ▓▓▓▓▓▓▓▓░░ 88%                              │
│                                                         │
│  ── 约束参数 ──────────────────────────────────────     │
│  ⚙️ 工期≤7天  |  成本≤¥300  |  安全系数≥1.5          │
│                                                         │
│  ── 执行工程 ──────────────────────────────────────     │
│  🏗️ 工程A：场景适配        [已完成]  proj-001          │
│  🏗️ 工程B：资源调度        [已完成]  proj-002          │
│  🏗️ 工程C：安全保障        [已完成]  proj-003          │
│                                                         │
│  ── 任务列表 ──────────────────────────────────────     │
│  📋 task-101  场景勘测       ✓已完成   mazi            │
│  📋 task-102  资源调配       ✓已完成   guzi            │
│  📋 task-103  方案制定       ✓已完成   gangzi          │
│  📋 task-104  应急响应启动   ✓已完成   kouzi           │
│  📋 task-105  现场处置       ✓已完成   mazi             │
│  📋 task-106  人员疏散       ✓已完成   guzi             │
│  📋 task-107  事后评估       ✓已完成   kouzi            │
│                                                         │
│  ── 流程路径 ──────────────────────────────────────     │
│  🔀 [启动应急响应] → [泄漏源控制] →                     │
│     [警戒与疏散] → [环境监测]                           │
│                                                         │
│  ── 执行摘要 ──────────────────────────────────────     │
│  💬 "本方案采用快速响应策略，通过多工程并行推进，         │
│      在7天内完成应急处置，成本控制在¥300以内。"           │
│                                                         │
│  ── 操作 ─────────────────────────────────────────     │
│  [💾 复制此方案]  [📊 对比其他方案]  [🔀 查看流程图]   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 复制方案功能

点击"复制此方案"按钮：
1. 弹出一个确认框，显示要复制的方案
2. 输入新目标名称
3. 系统根据方案B的执行链创建新目标：
   - 复制工程列表（新建，status=draft）
   - 复制任务列表（新建，status=todo）
   - 复制工作流
   - 复制约束参数
4. 新目标 mode = 'normal'（直接执行，不再探索）
5. 或者 mode = 'optimization'（在方案B基础上继续优化）

---

## 五、API 设计

### GET `/goals/{goal_id}/solutions/{solution_id}/execution-chain`

获取方案的完整执行链：

```json
{
  "solution_id": "sol-xxx",
  "projects": [...],
  "tasks": [...],
  "workflow": {...},
  "execution_summary": "..."
}
```

### POST `/goals/{goal_id}/solutions/{solution_id}/replicate`

复制方案创建新目标：

Request:
```json
{
  "new_goal_name": "新目标名称",
  "target_mode": "normal",
  "reuse_projects": false
}
```

Response:
```json
{
  "new_goal_id": "goal-new-xxx",
  "new_projects": ["proj-new-001", ...],
  "new_tasks": ["task-new-101", ...],
  "ok": true
}
```

---

## 六、实现优先级

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | 方案详情展示 | 在方案对比卡片中展开查看执行链 |
| P0 | 工程列表展示 | 显示方案关联的工程 |
| P0 | 任务列表展示 | 显示方案关联的任务 |
| P1 | 流程路径展示 | 显示工作流步骤和状态 |
| P1 | 执行摘要 | AI生成的方案执行摘要 |
| P2 | 复制方案功能 | 一键复制方案创建新目标 |

---

## 七、与其他模式的关系

| 模式 | 方案透明度 | 复制能力 |
|------|-----------|---------|
| 常规模式 | 无方案概念 | N/A |
| **探索模式** | **必须透明** | **必须可复制** |
| 迭代模式 | 透明（工程视角） | 可复制（沿用工程链） |

探索模式是**实验性**的，目标是找到最优解；找到之后必须能**复制**执行。

迭代模式是**执行性**的，每轮迭代本身就是一个完整工程；收敛即完成。

---

## 八、Sprint 81 待办

- [ ] 后端：GET `/solutions/{id}/execution-chain` 端点
- [ ] 后端：POST `/solutions/{id}/replicate` 端点
- [ ] 前端：方案详情展开面板
- [ ] 前端：工程列表组件
- [ ] 前端：任务列表组件
- [ ] 前端：流程路径展示
- [ ] 前端：复制方案按钮
- [ ] 测试：用现有探索模式目标验证方案执行链显示

---

## 九、验收标准

**功能验收**：
- [ ] 点击方案对比卡片中的任意方案，能展开看到完整执行链
- [ ] 执行链显示：工程列表（名称+状态）、任务列表（名称+状态+负责人）
- [ ] 执行链显示：流程路径（步骤+状态）
- [ ] "复制此方案"按钮可用，复制后创建的新目标包含相同的工程和任务
- [ ] 探索模式选定最优方案后，能在新目标里看到相同的工程/任务/流程


---


# 生命周期管理：激活/暂停/再激活

> **日期**：2026-05-14
> **触发**：Nexus 全流程体验发现缺少统一的暂停/恢复机制

---

## 一、需求定义

### 1.1 三层生命周期

```
Goal
 ├── activate()   → draft → in_progress
 ├── pause()      → in_progress → paused   （级联暂停所有子 Project）
 └── resume()      → paused → in_progress （子任务从未完成处进入 todo）
 │
 ├── Project
 │   ├── activate()  → created/draft → active
 │   ├── pause()    → active → paused （级联暂停所有子 Task）
 │   └── resume()   → paused → active  （Task 从未完成处进入 todo）
 │   │
 │   └── Task
 │       ├── dispatch() → todo → in_progress
 │       ├── pause()   → in_progress → paused
 │       └── resume()  → paused → todo （重新派发）
```

### 1.2 暂停语义

**立即停止**：不是"等当前任务做完再停"，是立即发停止信号。

**级联规则**：
- Goal.pause() → 所有 Project 暂停 → 所有 in_progress Task 暂停
- Project.pause() → 所有 Task 暂停（无论 goal 是否暂停）
- Task.pause() → 只停当前 Task

**暂停状态下的任务**：保持在 `paused` 状态，不回退到 `todo`。

### 1.3 再激活语义

**从头恢复 vs 从断点恢复**：
- Task: paused → todo（从头重新派发，不保留中间状态）
- Project: paused → active（Project 重启，等待派发子任务）
- Goal: paused → in_progress（重新启动调度器）

---

## 二、API 设计

### 2.1 Goal 级

| 操作 | 端点 | 状态变化 |
|------|------|---------|
| 激活 | `POST /goals/{goal_id}/activate` | draft → in_progress |
| 暂停 | `POST /goals/{goal_id}/pause` | in_progress → paused |
| 再激活 | `POST /goals/{goal_id}/resume` | paused → in_progress |

### 2.2 Project 级

| 操作 | 端点 | 状态变化 |
|------|------|---------|
| 激活 | `POST /projects/{project_id}/activate` | created/draft → active |
| 暂停 | `POST /projects/{project_id}/pause` | active → paused |
| 再激活 | `POST /projects/{project_id}/resume` | paused → active |

### 2.3 Task 级（已有部分）

| 操作 | 端点 | 状态变化 |
|------|------|---------|
| 派发 | scheduler tick | todo → in_progress |
| 暂停 | `POST /tasks/{task_id}/pause` | in_progress → paused |
| 再激活 | `POST /tasks/{task_id}/resume` | paused → todo |

---

## 三、数据库字段

### goals 表

| 字段 | 类型 | 说明 |
|------|------|------|
| status | VARCHAR(20) | `draft` / `in_progress` / `paused` / `completed` / `failed` |

新增 `paused` 状态。

### projects 表

| 字段 | 类型 | 说明 |
|------|------|------|
| status | VARCHAR(20) | `created` / `active` / `paused` / `completed` / `failed` |

新增 `paused` 状态。

### tasks 表

| 字段 | 类型 | 说明 |
|------|------|------|
| status | VARCHAR(20) | `todo` / `in_progress` / `paused` / `done` / `failed` / `timeout` |

`paused` 已存在，无需修改。

---

## 四、实现逻辑

### 4.1 Goal.pause()

```python
def pause_goal(goal_id: str, db: Session):
    # 1. 更新 goal 状态
    db.execute(text("UPDATE goals SET status='paused' WHERE id=:gid"), {"gid": goal_id})
    
    # 2. 找出该 goal 下所有 active project
    projects = db.execute(text(
        "SELECT id FROM projects WHERE goal_id=:gid AND status='active'"
    ), {"gid": goal_id}).fetchall()
    
    for proj in projects:
        # 3. 每个 project 暂停
        pause_project(proj.id, db)
    
    db.commit()
```

### 4.2 Project.pause()

```python
def pause_project(project_id: str, db: Session):
    # 1. 更新 project 状态
    db.execute(text("UPDATE projects SET status='paused' WHERE id=:pid"), {"pid": project_id})
    
    # 2. 找出该 project 下所有 in_progress task
    tasks = db.execute(text(
        "SELECT id FROM tasks WHERE project_id=:pid AND status='in_progress'"
    ), {"pid": project_id}).fetchall()
    
    for task in tasks:
        # 3. 向 Agent 发停止信号（通过 agent heartbeat 机制）
        send_stop_signal(task.id)
        # 4. 更新任务状态
        db.execute(text("UPDATE tasks SET status='paused' WHERE id=:tid"), {"tid": task.id})
    
    db.commit()
```

### 4.3 Task.resume()

```python
def resume_task(task_id: str, db: Session):
    task = db.query(Task).filter(Task.id == task_id).first()
    task.status = TaskStatus.TODO  # 回到 todo，重新派发
    # 清除已分配的 agent
    task.assigned_agent = None
    task.started_at = None
    db.commit()
```

### 4.4 Agent 停止信号机制

Task 被暂停时，需要通知 Agent 停止执行。两种方式：

**方式 A：心跳响应**
- Agent 每次 heartbeat，Nexus 返回当前待停止的 task_ids
- Agent 收到后自行停止对应任务

**方式 B：直接 kill 进程（不推荐）**
- 太暴力，可能导致数据不一致

推荐方式 A，扩展现有的 heartbeat 响应：

```python
# Agent heartbeat 响应
{
    "pending_stops": ["task-id-1", "task-id-2"]
}
```

---

## 五、现有代码整合

### 5.1 已有端点

- `PATCH /goals/{goal_id}/status` — 手动改状态（需扩展支持 pause/resume 语义）
- `POST /goals/{goal_id}/activate` — Sprint 81 新增（只改状态，不级联）
- Task pause/resume — 不存在，需新增

### 5.2 整合方案

在 `goals.py` 中扩展：
- `POST /goals/{goal_id}/pause` — 调用 pause_goal()
- `POST /goals/{goal_id}/resume` — 调用 resume_goal()

在 `projects.py` 中新增：
- `POST /projects/{project_id}/pause`
- `POST /projects/{project_id}/resume`

在 `tasks.py` 中新增：
- `POST /tasks/{task_id}/pause`
- `POST /tasks/{task_id}/resume`

---

## 六、状态机图

### Goal 状态机

```
   [draft]
      │ activate()
      ↓
   [in_progress] ←──────────┐
      │                      │
      │ pause()              │ resume()
      ↓                      │
   [paused] ────────────────┘
      │
      │ complete()
      ↓
   [completed]
```

### Task 状态机（已有）

```
   [todo]
      │ dispatch (scheduler)
      ↓
   [in_progress]
      │ pause()     complete()     fail()
      ↓           ↓              ↓
   [paused]    [done]         [failed]
      │
      │ resume()
      ↓
   [todo] (重新派发)
```

---

## 七、Sprint 82 待办

- [ ] DB: goals 表新增 `paused` 状态
- [ ] DB: projects 表新增 `paused` 状态（如果还没有）
- [ ] API: `POST /goals/{id}/pause` — Goal 暂停 + 级联
- [ ] API: `POST /goals/{id}/resume` — Goal 再激活
- [ ] API: `POST /projects/{id}/pause` — Project 暂停 + 级联
- [ ] API: `POST /projects/{id}/resume` — Project 再激活
- [ ] API: `POST /tasks/{id}/pause` — Task 暂停
- [ ] API: `POST /tasks/{id}/resume` — Task 再激活（→ todo）
- [ ] Heartbeat: 扩展 `pending_stops` 响应
- [ ] 前端: Goal/Project/Task 三级的暂停/恢复按钮
- [ ] 测试: 级联暂停验证
