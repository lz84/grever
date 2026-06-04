# Sprint 29：核心流程打通

**日期**: 2026-04-18  
**优先级**: P0（最高）  
**目标**: 跑通「Goal → 匹配 Scenario → 实例化 Workflow → 对话修正 → 拆分 Project → 创建 Task」完整流程

---

## 一、现状分析（2026-04-18 审计结果）

### 已有 ✅

| 模块 | 状态 | 说明 |
|------|------|------|
| Goal CRUD | ✅ | 创建/列表/详情可用 |
| Project CRUD | ✅ | 创建/列表/详情可用 |
| Task CRUD | ✅ | 创建/列表/完成/失败可用 |
| Scenario CRUD | ✅ | 有 16 条数据，但**全缺 template_dag** |
| Workflow CRUD | ✅ | 创建/列表/详情可用 |
| Workflow 可视化编辑 | ✅ | Sprint 26 完成，支持拖拽/连线/删除/添加 |
| Goal 树状图 | ❌ | API 返回 404 |
| Goal 自动分解 | ❌ | API 返回 500 |
| Agent 匹配 | ✅ | Sprint 23 完成 |
| 争议管理 | ✅ | Sprint 27 完成 |
| 成果物共享 | ✅ | Sprint 28 完成 |

### 缺失 ❌

| 环节 | 需求 | 现状 | 优先级 |
|------|------|------|--------|
| 1. Scenario 模板 | Scenario 需要有 template_dag（DAG 结构） | 所有 Scenario 的 template_dag 为 NULL | P0 |
| 2. 匹配 Scenario | Goal 创建时自动/手动匹配 Scenario | 有 Grasp plans 检索，但**未与 Goal 创建联动** | P0 |
| 3. 实例化 Workflow | 从 Scenario.template_dag 生成 Workflow | `POST /workflows/from-goal` 返回 404 | P0 |
| 4. 对话式编辑 | 用自然语言修正 Workflow | Sprint 26 做的是可视化编辑，**对话式未实现** | P1 |
| 5. Goal → Project 拆分 | Workflow 的阶段自动创建 Project | **完全未实现** | P0 |
| 6. Project 级 Workflow | 每个 Project 匹配 Scenario 实例化 | **完全未实现** | P1 |
| 7. 节点 → Task | Workflow 节点判断后创建 Task | Workflow activate 有，但**与 Goal 流程断裂** | P0 |

---

## 二、核心流程定义

### 2.1 完整流程（复杂场景：地震救援）

```
用户输入: "某地7.2级地震救援"
  ↓
1. Goal 创建 → status = draft
  ↓
2. 匹配 Goal 级 Scenario
  ├─ 有高匹配 Scenario → 推荐 Top 1-3 → 用户选择
  └─ 无匹配 → LLM 自动生成 Workflow（冷启动）
  ↓
3. 实例化 Goal 级 Workflow
  ├─ 从 Scenario.template_dag 复制 → workflow.dag
  ├─ workflow.status = draft
  └─ 关联到 Goal.workflow_id
  ↓
4. 用户修正 Workflow（对话式 or 可视化）
  ├─ 对话式: "把阶段2和3合并" → LLM 解析 → 修改 DAG
  └─ 可视化: 拖拽/连线/删除/添加节点
  └─ 确认后 → workflow.status = confirmed
  ↓
5. Goal 状态更新: draft → planned
  ↓
6. Goal 级 Workflow 的阶段 → 自动拆分为 Project
  ├─ 每个阶段 = 一个 Project
  ├─ Project.status = pending
  └─ Project.phase_order = 阶段顺序
  ↓
7. 每个 Project 匹配 Project 级 Scenario
  ├─ 有匹配 → 实例化 Project 级 Workflow
  └─ 无匹配 → LLM 自动生成
  ↓
8. 用户修正 Project 级 Workflow → 确认
  ↓
9. Project 级 Workflow 的节点 → 判断类型
  ├─ execution → 创建 Task → 分配 Agent
  ├─ notification → 不创建 Task（直接执行通知）
  ├─ decision → 等待用户/主Agent 确认
  └─ milestone → 标记点，不创建 Task
  ↓
10. Task 派发执行
```

### 2.2 精简流程（中等任务：调动应急物资）

```
用户直接启动 Project: "调动应急物资到 A 地"
  ↓
匹配 Project 级 Scenario → 实例化 Workflow
  ↓
用户修正 → 确认
  ↓
节点 → 创建 Task → 分配 Agent → 执行
```

### 2.3 极简流程（短任务：发送通知）

```
直接创建 Task → 分配 Agent → 执行
```

---

## 三、Sprint 29 任务分解

> **规则**：每个子任务 = 后端 API + 前端页面 + 集成验证

### Task 29-1: Scenario 模板填充 + 实例化 API

**目标**: 让 Scenario 有实际的 template_dag，并实现从 Scenario 实例化 Workflow

| 子项 | 后端 | 前端 | 验证 |
|------|------|------|------|
| 29-1.1 | 填充 3 个 Scenario 模板（地震救援/洪水应急/危化品泄漏）的 template_dag | — | `template_dag` 非空 |
| 29-1.2 | 新增 API: `POST /api/v1/scenarios/{id}/instantiate-workflow` — 从 Scenario 实例化 Workflow | — | 实例化后 Workflow 有完整 DAG |
| 29-1.3 | 新增 API: `POST /api/v1/goals/{id}/match-scenario` — 为 Goal 匹配 Scenario（返回 Top 3） | — | 返回匹配结果列表 |
| 29-1.4 | — | Goal 创建页新增「方案选择」步骤 | 创建 Goal 时可从推荐方案中选择 |

**验收标准**:
- 3 个 Scenario 有完整的 template_dag
- `match-scenario` 返回匹配的 Scenario 列表
- `instantiate-workflow` 从 template_dag 生成完整 Workflow（含 nodes + edges）

### Task 29-2: Goal → Project 自动拆分

**目标**: Workflow 确认后，阶段自动拆分为 Project

| 子项 | 后端 | 前端 | 验证 |
|------|------|------|------|
| 29-2.1 | 新增 API: `POST /api/v1/workflows/{id}/confirm-and-split` — 确认 Workflow 并拆分为 Project | — | Project 自动创建，phase_order 正确 |
| 29-2.2 | Project 创建时自动关联 Goal + 继承 priority | — | Project.goal_id 正确 |
| 29-2.3 | — | Project 列表页按 phase_order 排序 | 列表按阶段顺序显示 |
| 29-2.4 | — | Goal 详情页显示关联的 Project 列表 | 能看到所有阶段 |

**验收标准**:
- Workflow 确认后自动创建 N 个 Project（N = Workflow 阶段数）
- 每个 Project 有正确的 goal_id, phase_order, priority
- Project 列表按顺序显示

### Task 29-3: Workflow 对话式编辑

**目标**: 用自然语言修正 Workflow（LLM 解析指令 → 修改 DAG）

| 子项 | 后端 | 前端 | 验证 |
|------|------|------|------|
| 29-3.1 | 新增 API: `POST /api/v1/workflows/{id}/dag/chat` — 对话式编辑（LLM 解析指令） | — | 输入指令 → DAG 正确修改 |
| 29-3.2 | — | Workflow 编辑页新增「对话编辑」面板 | 输入 → 实时预览 → 确认保存 |

**对话编辑示例指令**:
- "把阶段2和3合并"
- "在阶段1后面加一个资源评估"
- "删除最后一个阶段"
- "把阶段3移到最前面"
- "在物资调度和运输执行之间加一个审批环节"

**验收标准**:
- 能正确解析 5 种以上修改指令
- 每次修改后 DAG 保持有效性（无环）
- 修改后自动同步 workflow_steps 表

### Task 29-4: 节点 → Task 创建 + Agent 分配

**目标**: Workflow 确认后，execution 节点自动创建 Task 并分配 Agent

| 子项 | 后端 | 前端 | 验证 |
|------|------|------|------|
| 29-4.1 | 修改 `confirm-and-split`: 为 Project 级 Workflow 的 execution 节点创建 Task | — | Task 数量 = execution 节点数 |
| 29-4.2 | Task 创建时自动关联 Agent（基于 agent_requirements 匹配） | — | Task 有 assigned_agent |
| 29-4.3 | — | Task 列表页按依赖关系排序 | 列表显示依赖链 |
| 29-4.4 | — | Task 详情页显示关联的 Workflow 节点 | 能看到来源节点 |

**验收标准**:
- 每个 execution 节点 → 1 个 Task
- Task 有正确的 dependencies（基于 DAG 边关系）
- Agent 自动匹配分配

### Task 29-5: 端到端集成测试

**目标**: 用"地震救援"场景跑通完整流程

| 子项 | 验证内容 |
|------|----------|
| 29-5.1 | Goal 创建 → 匹配 Scenario（地震救援预案） |
| 29-5.2 | 实例化 Goal 级 Workflow（6 个阶段） |
| 29-5.3 | 对话式修正: "合并阶段5和6" → DAG 更新 |
| 29-5.4 | 确认并拆分 → 5 个 Project 自动创建 |
| 29-5.5 | 每个 Project 匹配 Project 级 Scenario → 实例化 Workflow |
| 29-5.6 | execution 节点 → Task 创建 + Agent 分配 |
| 29-5.7 | Task 列表按依赖关系正确排序 |

---

## 四、数据库变更

### 4.1 现有表检查

| 表 | 状态 | 需要变更 |
|----|------|----------|
| scenarios | ✅ 有 template_dag 字段 | 需要填充数据 |
| workflows | ✅ 有 dag 字段 | 无需变更 |
| projects | ✅ 有 workflow_id, phase_order | 无需变更 |
| tasks | ✅ 有 workflow_step_id | 无需变更 |

### 4.2 迁移脚本

```sql
-- migrations/014_sprint29_scenario_templates.sql

-- 填充地震救援 Scenario 模板
UPDATE scenarios SET 
    template_dag = '{"nodes":[...],"edges":[...]}'
WHERE id = 'scenario-earthquake-001';

-- 确保 workflow_id 字段在 projects 表存在
ALTER TABLE projects ADD COLUMN IF NOT EXISTS workflow_id VARCHAR(36);
```

---

## 五、API 设计

### 5.1 新增 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/goals/{id}/match-scenario` | 为 Goal 匹配 Scenario（返回 Top 3） |
| `POST` | `/api/v1/scenarios/{id}/instantiate-workflow` | 从 Scenario 实例化 Workflow |
| `POST` | `/api/v1/workflows/{id}/confirm-and-split` | 确认 Workflow 并拆分为 Project |
| `POST` | `/api/v1/workflows/{id}/dag/chat` | 对话式编辑 Workflow |
| `GET` | `/api/v1/workflows/{id}/dag/suggestions` | 获取 LLM 优化建议 |

### 5.2 请求/响应示例

**match-scenario**:
```json
// POST /api/v1/goals/{goal_id}/match-scenario
{
  "goal_id": "goal-xxx",
  "goal_title": "某地7.2级地震救援"
}

// Response
{
  "matches": [
    {
      "scenario_id": "scenario-earthquake-001",
      "name": "地震救援总体预案",
      "match_score": 0.95,
      "level": "goal",
      "trust_level": "high",
      "usage_count": 42
    }
  ]
}
```

**confirm-and-split**:
```json
// POST /api/v1/workflows/{wf_id}/confirm-and-split
{}

// Response
{
  "workflow_id": "wf-xxx",
  "workflow_status": "confirmed",
  "projects_created": 5,
  "project_ids": ["proj-1", "proj-2", "proj-3", "proj-4", "proj-5"],
  "tasks_created": 18
}
```

**dag/chat**:
```json
// POST /api/v1/workflows/{wf_id}/dag/chat
{
  "instruction": "把阶段2和3合并"
}

// Response
{
  "success": true,
  "dag": { "nodes": [...], "edges": [...] },
  "changes": [
    {"action": "merged", "from": ["step-2", "step-3"], "to": "step-2-3"}
  ]
}
```

---

## 六、前端页面变更

### 6.1 Goal 创建页改造

```
旧: 输入标题 → 描述 → 创建
新: 输入标题 → 描述 → [自动推荐 Scenario] → 选择方案 or 跳过 → 创建
```

### 6.2 Workflow 编辑页改造

```
旧: 纯可视化编辑（拖拽/连线）
新: 可视化编辑 + 对话编辑 双模式
    ├─ 可视化: 拖拽/连线/删除/添加（Sprint 26 已有）
    └─ 对话: 右侧面板，输入自然语言指令 → LLM 解析 → 预览修改 → 确认
```

### 6.3 Goal 详情页改造

```
新增:
- 关联的 Project 列表（按 phase_order 排序）
- 每个 Project 的状态（pending/in_progress/completed）
- Project 级 Workflow 缩略图
```

---

## 七、Done 标准

### 每个子任务

- ✅ 单元测试通过
- ✅ API curl 验证
- ✅ 页面正常渲染
- ✅ 端到端流程跑通

### Sprint 29 整体

- ✅ "地震救援"完整流程从 Goal 创建到 Task 派发全部跑通
- ✅ 对话式编辑能正确处理 5 种以上修改指令
- ✅ 自动拆分后 Project 和 Task 数量正确
- ✅ Agent 自动匹配分配成功

---

*创建时间: 2026-04-18 09:00*  
*创建人: 刚子*
