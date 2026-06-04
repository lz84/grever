# 驾驭协同模块审计报告

**审计日期**: 2026-04-25
**审计方法**: 数据流追踪 + 断点检查 + 不对称分析 + 数据库实际结构验证
**审计范围**: 目标/项目/任务/工作流/Agent/场景/争议 全链路

---

## 一、数据流全景图

```
Goal（目标）
  ├── 创建方式：CreateGoal.tsx 表单 → POST /goals/
  ├── 分解方式：auto-decompose（LLM → 项目预览） → decompose/submit（创建项目）
  ├── 场景匹配：GoalDetail 手动匹配 → match-for-goal → instantiate-workflow → 回写 goal
  ├── 状态联动：PATCH /goals/{id}/status → 级联 projects + tasks
  │
  └── Project（项目）
       ├── 创建方式：auto-decompose submit / 手动创建 / workflow-split
       ├── 关联：goal_id（外键）
       ├── 包含：tasks（通过 project_id 关联）
       ├── 独立 DAG：/projects/{id}/diagram（按 project_id 过滤 tasks 构建）
       └── 状态级联：PATCH /projects/{id}/status → 联动 in_progress/todo 任务
            │
            └── Task（任务）
                 ├── 创建方式：手动创建 / workflow activate / decompose
                 ├── 关联：goal_id + project_id（双关联）
                 ├── 分配：assigned_agent（字符串） / agent_assignments 表
                 ├── 完成：POST /tasks/{id}/complete → 更新 goal progress + scenario feedback
                 ├── 失败：POST /tasks/{id}/fail → 重试机制（3次）→ blocked
                 ├── 依赖：task_dependencies 表 + depends_on JSON
                 └── 追踪：traces 表（内存 + 数据库双写）

  Workflow（工作流）
  ├── 创建方式：scenario instantiate / from-goal
  ├── 关联：goal_id + parent_scenario_id + project_id
  ├── 步骤：workflow_steps 表
  ├── 激活：POST /workflows/{id}/activate → 为每个 step 创建 Task
  ├── 事件监听：task_completed → 更新 step → 检查 workflow 完成
  └── 拆分：workflow-split → 拆分为 Projects

  Agent（智能体）
  ├── 注册：POST /agents/ → agents 表
  ├── 心跳：POST /agents/{id}/heartbeat → 更新 last_heartbeat + 分配 pending tasks
  ├── 能力匹配：capabilities JSON → 任务能力需求子集匹配
  ├── 负载：load + current_tasks → 负载上限检查
  ├── 分配方式：
  │   - 心跳拉取：agent heartbeat → 返回 pending tasks
  │   - 直接分配：POST /tasks/{id}/assign
  └── 绑定：agent_mcp_bindings 表（MCP 工具绑定）

  Scenario（场景）
  ├── 匹配：POST /scenarios/match-for-goal/{goal_id}（基于关键词 + 文本相似度）
  ├── 实例化：POST /scenarios/{id}/instantiate-workflow → 创建 workflow
  ├── 反馈：task complete → 更新 success_count/failed_count/success_rate
  └── 进化：MAK-228 → 自动版本升级 + 状态迁移

  Dispute（争议）
  ├── 发起：POST /disputes/
  ├── 讨论：POST /disputes/{id}/discuss → 自动切换到 discussing
  ├── 仲裁：POST /disputes/{id}/arbitrate
  └── 存储：discussion_log JSON 字段
```

---

## 二、发现的问题（按严重程度排序）

### 🔴 P0：数据一致性问题

#### 问题 1：双数据源不同步 — ReinsServer 内存 vs SQLite

**严重程度**: 🔴 致命

**数据流断点**：
```
数据库 → 启动时加载到 ReinsServer 内存 → 后续写操作只写 DB，不更新内存
```

**证据**：`server.py` 的 `_lifespan` 中，启动时从 SQLite 读取所有数据到内存（agents, goals, projects, tasks, disputes），但后续 API 操作：
- `goals.py` 的 `create_goal` → 只写 DB，不更新内存
- `tasks.py` 的 `create_task` → 只写 DB，不更新内存
- `tasks.py` 的 `complete_task` → 只写 DB，不更新内存

**影响**：`reins.list_goals()`, `reins.list_tasks()` 等返回的是**陈旧内存数据**，与数据库不一致。Dashboard 和全局搜索部分用内存，部分用 DB，返回结果不一致。

**修复建议**：统一使用 DB 作为唯一数据源，删除内存存储层。或者每次写操作同步更新内存。

---

#### 问题 2：tasks 表 goal_id 类型不一致 — 导致过滤完全失效

**严重程度**: 🔴 高

**证据**：
- `tasks.py` 的 `list_tasks` 端点：`goal_id: Optional[int] = Query(None)` — 接收 int
- `tasks` 表实际结构：`goal_id VARCHAR(36)` — 存储 UUID 字符串
- `goals` 表实际结构：`id VARCHAR(32)` — UUID 字符串

**后果**：前端传入字符串 goal_id，后端按 int 过滤 → 永远不匹配 → 按 goal_id 过滤任务返回空。

`GoalDetail.tsx` 被迫使用 client-side 过滤：
```typescript
const goalTasks = allTasks.filter((t: any) => t.goal_id === goalId)
```
当任务量大时（>1000），加载全部任务再前端过滤会造成严重性能问题。

**修复建议**：后端 `goal_id` 参数改为 `Optional[str]`，直接 SQL 过滤。

---

#### 问题 3：Goal.progress 计算混乱 — 三套计算逻辑互不协调

**严重程度**: 🔴 高

**三套计算逻辑**：

| 位置 | 计算方式 | 触发时机 |
|------|---------|---------|
| `tasks.py:complete_task` | 统计 goal 下所有 task，done/total | 单个 task 完成时 |
| `workflows.py:_on_task_completed` | 统计 workflow 下所有 step，done/total | workflow event 触发时 |
| `server.py:update_goal_status` | 不计算，只改 status | 状态切换时 |

**问题**：
1. 一个 task 同时属于 goal 和 workflow 时，可能被两套系统重复计算
2. `tasks.py` 统计所有 task（包括未分配、未开始的），但一个 goal 的 task 可能分布在多个 project 中，数据来源不完整
3. `workflows.py` 的 event 监听可能未被正确注册（依赖 `_db_manager` 初始化，但多个模块都在初始化它）
4. 两套计算可能产生不同的 progress 值

**修复建议**：统一为一套计算逻辑，明确"progress 基于 task 还是基于 workflow step"。

---

#### 问题 4：`datetime.utcnow()` 与 `datetime.now()` 混用

**严重程度**: 🟡 中

**证据**：
- `goals.py`: 已改为 `datetime.now()`（上次重构）
- `tasks.py`: 仍然大量使用 `datetime.utcnow()`（17 处）
- `server.py`: 使用 `datetime.utcnow()`（11 处）
- `assignment.py`: 使用 `datetime.utcnow()`（2 处）
- `workflows.py`: 使用 `datetime.now()`（5 处）
- `dispute_manage.py`: 使用 `datetime.now().isoformat()`

**影响**：混用导致时间戳不一致，影响排序、过期判断、心跳检测等。Python 3.12 已弃用 `utcnow()`。

---

#### 问题 5：task 的 `assigned_agent` 与 `agent_assignments` 表不同步

**严重程度**: 🟡 中

**数据流断裂**：
```
创建 task → assigned_agent = 字符串（直接写在 tasks 表）
分配 task → POST /tasks/{id}/assign → 只更新 tasks.assigned_agent
心跳拉取 → 查询 tasks WHERE assigned_agent = :agent_id
但：agent_assignments 表完全独立
```

**证据**：
- `agent_assignments` 表有 1 条记录，但所有 task 的 `assigned_agent` 字段为空
- 两个系统互不通信：tasks 表写了 assigned_agent，agent_assignments 表不知道
- `heartbeat` 端点直接从 tasks 表查 `assigned_agent`，不走 agent_assignments

**修复建议**：二选一：
- 方案 A：废弃 agent_assignments 表，只用 tasks.assigned_agent
- 方案 B：每次分配/解除时同步写 agent_assignments 表

---

### 🟡 P1：功能缺陷

#### 问题 6：Dashboard Stats 全表扫描 — 无性能保护

**严重程度**: 🟡 中

**证据**：`dashboard_stats.py`:
```python
tasks_result = db.execute(text("SELECT id, status, completed_at FROM tasks")).fetchall()
agents_result = db.execute(text("SELECT id, status FROM agents")).fetchall()
scenarios_result = db.execute(text("SELECT id FROM scenarios")).fetchall()
goals_result = db.execute(text("SELECT id, status FROM goals")).fetchall()
```

**问题**：
1. 每 30 秒全表扫描 4 张表（前端 refreshInterval = 30000ms）
2. 当 tasks 表增长到万级时，每次查询全表拖拽
3. 无索引：tasks(status), tasks(completed_at), goals(status) 都没有索引

**修复建议**：
- 加 COUNT 查询替代 SELECT *：`SELECT COUNT(*) FROM tasks WHERE status = 'in_progress'`
- 或物化视图/定时任务预计算

---

#### 问题 7：场景匹配算法过于简单 — 仅 3 个硬编码类别

**严重程度**: 🟡 中

**证据**：`scenario_workflow.py` 的 `_calc_score`:
```python
cat_kws = {
    "earthquake": ["地震", "震级", "震源", "救援", "搜救", "震后"],
    "flood": ["洪水", "洪涝", "水位", "暴雨", "防汛", "泄洪", "淹"],
    "chemical": ["危化品", "泄漏", "化工", "有毒气体", "化学品", "泄漏事故"],
}
```

**问题**：
1. 新增场景类别必须修改代码（不能通过配置扩展）
2. 匹配精度低：`difflib.SequenceMatcher` 在中文场景下效果差
3. 只匹配 `level = 'goal'` 的场景，忽略 project/task 级别

**修复建议**：使用 LLM embedding 或配置化关键词字典。

---

#### 问题 8：Workflow 激活创建 Task 时 project_id = None

**严重程度**: 🟡 中

**证据**：`workflows.py` 的 `activate_workflow`:
```python
task_data = {
    ...
    "project_id": None,  # Workflow 没有 project 概念
    ...
}
```

**问题**：
- Workflow 从 scenario 实例化时，关联的是 goal，不是 project
- 但 workflow steps 应该映射到具体的 project
- 创建的 task 没有 project_id → 在 GoalDetail 的"关联项目"列表中看不到
- 这些 task 只能通过 goal_id 过滤，失去了 project 层级

**修复建议**：激活 workflow 时，将 steps 映射到对应 project（通过 workflow.project_id 或 goal 的 projects 映射）。

---

#### 问题 9：`delete_project` 没有级联删除 tasks

**严重程度**: 🟡 中

**证据**：`projects.py`:
```python
@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
```

1. `project_id` 参数类型是 `int`，但实际是 UUID 字符串
2. 只删除 project 记录，不删除关联的 tasks
3. 对比 `goals.py` 的 `delete_goal` 已修复（有级联删除），`projects.py` 没有

**修复建议**：改为 `str` 类型 + 增加级联删除。

---

#### 问题 10：任务列表前端全量加载 — 无后端分页

**严重程度**: 🟡 中

**证据**：`TaskList.tsx`:
```typescript
const data = await tasksApi.list(params)  // 返回所有任务
```

后端 `list_tasks` 虽然有 `skip/limit` 参数，但前端未传递。所有分页在前端做：
```typescript
const paginatedTasks = filteredTasks.slice(startIndex, startIndex + ITEMS_PER_PAGE)
```

**问题**：任务量增长后，首次加载传输大量数据，前端切片只是掩耳盗铃。

---

### 🟢 P2：设计隐患

#### 问题 11：两套 Goal 创建路径并存

**证据**：
1. `goals.py` 的 `create_goal` 端点（被前端 CreateGoal.tsx 调用）
2. `server.py` 的内存 Goal 创建（通过 ReinsServer）
3. `workflow_split.py` 的拆分创建
4. `dag_conversation.py` 的对话式创建

**问题**：不同路径创建的 Goal 数据结构可能不一致，有的写 DB，有的写内存，有的两者都写。

---

#### 问题 12：task 的 `priority` 字段类型混乱

**严重程度**: 🟢 低

**数据库**：`priority INTEGER`（存储 0-5 的数字）

**后端 API**：
- `tasks.py:complete_task` 中按字符串比较（`'high'`, `'medium'`）
- `assignment.py` 中按字符串比较
- `server.py` 中同时处理 int 和 string

**前端**：
- `TaskList.tsx`: `priority: number`，0=P0, 1=P1, 2=P2, 3=P3
- `CreateGoal.tsx`: `priority: string`，'high', 'medium', 'low', 'P3'
- `api.ts` Goal interface: `priority: string | null`
- `api.ts` Task interface: 没有 priority 字段定义

**修复建议**：统一为一种类型（推荐保留 INT，前端做映射）。

---

#### 问题 13：EventBus 事件注册时机不确定

**证据**：`workflows.py`:
```python
def register_workflow_event_listeners():
    try:
        bus_manager = get_event_bus_manager()
        bus = bus_manager.get_adapter(None)
        if bus:
            bus.subscribe("task_completed", _on_task_completed)
```

这个函数在 `server.py` 的 `create_app` 中调用，但：
1. EventBus 可能未初始化（`bus_manager.get_adapter(None)` 返回 None）
2. 如果返回 None，事件监听器不会注册，但只打印警告不报错
3. 意味着 task 完成可能不会触发 workflow 状态更新，且无告警

---

#### 问题 14：争议讨论存储在 JSON 字段中 — 无结构化查询能力

**证据**：`disputes` 表的 `discussion_log` 是 JSON 文本字段。

**问题**：
- 无法按 agent 过滤讨论
- 无法按时间范围搜索
- 无法全文搜索讨论内容
- JSON 增长无限制，可能变得很大

**修复建议**：拆分为独立的 `dispute_messages` 表。

---

#### 问题 15：Dashboard 前端硬编码 workflow ID

**证据**：`TaskList.tsx`:
```typescript
fetch('/api/v1/workflows/wf-61068850')
  .then(r => r.json())
```

**问题**：硬编码 workflow ID，换个环境或数据就 404。

---

#### 问题 16：多个 API 端点重复注册

**证据**：`server.py` 中：
```python
app.include_router(dispute_manage_router)  # 第 1 次
...
app.include_router(dispute_manage_router)  # 第 2 次（底部）
```

以及：
```python
app.include_router(assignments_router)  # 第 1 次
...
app.include_router(assignments_router)  # 第 2 次（底部）
```

**影响**：FastAPI 可能报错或行为不确定。

---

## 三、数据库结构问题

### 表结构不一致

| 表 | 问题 |
|---|------|
| `tasks.goal_id` | VARCHAR(36)，但 `list_tasks` 用 int 过滤 |
| `tasks.priority` | INTEGER，但多处代码按字符串比较 |
| `tasks.project_id` | VARCHAR(36)，但 `projects.py` 的 project ID 也是 VARCHAR |
| `tasks.assigned_agent` | VARCHAR(36)，但 agents 表 id 也是 VARCHAR(36) — 没有外键约束 |
| `goals.parent_id` | VARCHAR(32)，但 goal id 是 VARCHAR(32) — 自引用但无约束 |
| `projects.goal_id` | VARCHAR(32)，但 goals.id 是 VARCHAR(32) — 无外键约束 |
| 所有表 | 无外键约束（SQLite 默认关闭 FK） |

### 缺少索引

以下查询频繁但无索引：
- `tasks(goal_id)` — 按目标过滤任务
- `tasks(project_id)` — 按项目过滤任务
- `tasks(status)` — 按状态过滤
- `tasks(assigned_agent)` — 按分配过滤
- `goals(status)` — 按状态过滤
- `workflows(goal_id)` — 按目标过滤
- `traces(task_id)` — 按任务查询追踪
- `traces(workflow_id)` — 按工作流查询

### 空表（0 行数据）

以下表从未写入数据：
- `agents` (0 行) — Agent 只注册到内存，不持久化
- `scenarios` (0 行) — 场景库为空
- `workflows` (0 行) — 工作流表为空
- `workflow_steps` (0 行) — 步骤表为空
- `cognitions` (0 行) — 认知表为空
- `artifacts` (0 行) — 成果物表为空
- `trace_events` (0 行) — 追踪事件表为空
- `trace_reports` (0 行) — 追踪报告表为空
- `task_activity_log` (0 行) — 活动日志表为空
- `task_failure_log` (0 行) — 失败日志表为空
- 等 18 张空表

---

## 四、数据流断点汇总

| # | 断点位置 | 数据丢失/不一致 | 影响范围 |
|---|---------|---------------|---------|
| 1 | DB → 内存 | 写后读不一致 | 全局 |
| 2 | task goal_id 过滤 | 按 goal_id 查 task 失效 | GoalDetail, Dashboard |
| 3 | Goal.progress | 三套算法产生不同值 | Dashboard, GoalDetail |
| 4 | assigned_agent vs agent_assignments | 分配数据分裂 | Agent 派发 |
| 5 | task complete → scenario feedback | scenario 表为空，反馈无目标 | 场景进化 |
| 6 | workflow activate → task project_id | 激活创建的 task 无 project | 项目穿透 |
| 7 | EventBus 可能未注册 | task 完成不触发 workflow 更新 | Workflow 状态 |
| 8 | heartbeat → agents 表 | Agent 心跳数据不持久化 | Agent 状态监控 |

---

## 五、优先级修复建议

### 立即修复（P0）
1. **统一数据源**：删除 ReinsServer 内存存储，所有 API 直接读 DB
2. **修复 goal_id 过滤**：`list_tasks` 的 goal_id 参数改为 str
3. **统一 progress 计算**：选定一套逻辑，删除其他

### 短期修复（P1）
4. 添加缺失索引
5. 修复 `delete_project` 级联删除 + 参数类型
6. Dashboard Stats 改为 COUNT 查询
7. EventBus 注册失败时告警
8. 修复端点重复注册

### 中期修复（P2）
9. priority 类型统一
10. agent_assignments 表同步或废弃
11. 场景匹配算法升级
12. task 前端分页改为后端分页
13. 讨论记录拆分为独立表

---

## 六、架构总结

**当前架构特点**：
- 双数据源（内存 + SQLite）导致一致性难以保证
- 多层 API 重叠（server.py 快捷端点 + 独立 router 文件）
- 类型系统不统一（int vs string 贯穿所有 ID 和枚举字段）
- 数据写入后缺少回写机制（如 scenario 匹配结果不回写 goal）

**核心建议**：
1. **SQLite 作为唯一数据源**，删除所有内存存储
2. **Pydantic 统一请求/响应**，消除 `Body(None)` 裸取
3. **类型对齐**：所有 ID 用 str，所有枚举用 string
4. **写入必回写**：任何关联操作必须更新双向引用
5. **数据流审查**：每次新增功能时，画数据流图确认没有断点

---

*报告生成时间: 2026-04-25 12:30*
*审计文件: 5 个前端页面 + 18 个后端 API 文件 + 31 张数据库表*
