# Sprint 36：项目级流程图 + 任务级联控制

**日期**: 2026-04-22
**优先级**: P0
**目标**: 项目有独立的 DAG 可视化和任务分解图，支持项目级暂停/激活

---

## 一、需求背景

场景有目标级和项目级，项目应该有自己独立的：
1. 流程图（DAG 可视化）
2. 任务分解图（树状结构）
3. 暂停/激活功能（级联到下属任务）

---

## 二、任务清单

### Task 36-1：后端 — 项目级 Workflow API

**目标**: 支持按 project_id 过滤查询工作流

| 端点 | 描述 | 优先级 |
|------|------|--------|
| `GET /api/v1/workflows?project_id={id}` | 返回项目专属工作流 | P0 |
| `GET /api/v1/workflows?goal_id={id}&project_id={id}` | 联合过滤 | P1 |
| `GET /api/v1/projects/{id}/diagram` | 项目级 DAG 数据（复用 workflow_diagram.py） | P0 |
| `GET /api/v1/projects/{id}/task-tree` | 项目级任务树（含子任务） | P0 |
| `PATCH /api/v1/projects/{id}/status` | 项目暂停/激活（级联任务） | P0 |

**实现要点**:
- `workflow_diagram.py` 已有 DAG 生成逻辑，需改为支持 project_id 过滤
- 任务树查询：`WHERE project_id = :pid` 包含 parent_id 层级关系
- 项目暂停时：`in_progress` → `on_hold`（仅进行中项目），任务 `in_progress` → `todo`

### Task 36-2：前端 — 项目详情页 Tab 改造

**目标**: 项目详情页改为 Tab 结构

| Tab | 内容 | 优先级 |
|-----|------|--------|
| 详情 | 基本信息、成员列表、状态 | P0 |
| 流程图 | 项目级 DAG 可视化（ReactFlow） | P0 |
| 任务分解 | 项目级任务树（ReactFlow 树状图） | P0 |

**实现要点**:
- 复用 `WorkflowDiagram.tsx` 组件，传入 `projectId` prop
- 复用 `GoalTreeView.tsx` 组件，改为项目过滤模式
- Tab 组件用 shadcn Tabs 或原生

### Task 36-3：前端 — 项目级 DAG 可视化

**目标**: 项目专属工作流 DAG

**验收**:
- DAG 节点 = 该项目专属的任务
- DAG 边 = 项目内任务依赖关系
- 节点点击可展开任务详情侧边栏
- 无白屏、无 console error

### Task 36-4：前端 — 项目级任务分解树

**目标**: 项目下任务的树状结构

**验收**:
- 根节点 = 项目名称
- 子节点 = 项目内任务（含父子关系）
- 节点颜色按状态区分（in_progress=蓝，done=绿，todo=灰）
- 点击任务节点 → 跳转执行详情页

### Task 36-5：后端 — 项目级暂停/激活级联

**目标**: 项目状态变更联动任务

| 项目操作 | 项目状态变化 | 任务联动 |
|----------|-------------|----------|
| 暂停 | `active` → `on_hold` | `in_progress` → `todo` |
| 激活 | `on_hold` → `active` | `todo` → `in_progress` |

**规则**:
- 已完成任务不受影响
- 已完成项目不能被暂停
- 已暂停项目不能被二次暂停

### Task 36-6：前端 — 项目详情页暂停/激活按钮

**目标**: 项目详情页有状态切换按钮

**验收**:
- 进行中 → 显示"暂停"按钮（调用 `PATCH /projects/{id}/status` → `on_hold`）
- 已暂停 → 显示"激活"按钮（调用 `PATCH /projects/{id}/status` → `active`）
- 已完成 → 显示按钮为灰色不可点
- 操作后页面状态即时刷新

---

## 三、验收标准

### 必做（P0）

- [ ] `GET /api/v1/workflows?project_id=proj-xxx` 返回项目工作流 + Steps
- [ ] `GET /api/v1/projects/{id}/task-tree` 返回项目任务树
- [ ] `PATCH /api/v1/projects/{id}/status` 级联更新任务状态
- [ ] 项目详情页有 Tab 切换（详情 / 流程图 / 任务分解）
- [ ] 流程图 Tab 渲染 DAG（节点=项目任务，边=依赖）
- [ ] 任务分解 Tab 渲染树状图（含父子关系）
- [ ] 项目有暂停/激活按钮，点击后任务状态同步变化

### 检验方法

| 检验项 | 方法 | 标准 |
|--------|------|------|
| API 数据 | curl `GET /api/v1/workflows?project_id=proj-xxx` | 返回该项目 worklfow JSON |
| DAG 可视化 | 浏览器打开项目详情 → 切流程图 Tab | ReactFlow 正常渲染 |
| 任务树 | 浏览器打开项目详情 → 切任务分解 Tab | 树状图正常展开 |
| 级联暂停 | curl 暂停项目 → 查任务状态 | in_progress 任务变为 todo |
| 端到端 | 浏览器：暂停项目 → 刷新页面 → 验证 | 页面状态+任务状态一致 |

### Done 定义

- ✅ 单测覆盖核心逻辑（项目级联、DAG 过滤）
- ✅ curl 验证所有 API 端点
- ✅ 浏览器验证 3 个 Tab 均正常渲染
- ✅ 端到端场景跑通（暂停→激活→状态验证）

---

## 四、执行顺序

1. **Task 36-1**（后端 API，基础数据层）
2. **Task 36-5**（后端级联逻辑）
3. **Task 36-2**（前端 Tab 结构）
4. **Task 36-3**（前端 DAG 可视化）
5. **Task 36-4**（前端任务树）
6. **Task 36-6**（前端暂停按钮）

---

## 五、依赖关系

```
36-1 (后端API) ──→ 36-3 (DAG)
              └──→ 36-4 (任务树)
36-5 (级联)  ──→ 36-6 (暂停按钮)
36-2 (Tab)   ──→ 36-3 + 36-4 + 36-6 (依赖 Tab 组件)
```

---

*创建时间: 2026-04-22 17:59*
*创建人: 刚子*
