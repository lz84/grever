# Sprint 85: 场景库差距分析

> 日期: 2026-05-20  
> 目标: 将场景库重构为与目标相同的层级结构（Project→Task）  
> 核心洞察: **场景 = 目标的结构，只是不展示执行部分**

---

## 一、核心理念对比

### 1.1 Goal vs Scenario 的本质关系

| 维度 | Goal（目标） | Scenario（场景） |
|------|-------------|-----------------|
| **性质** | 实际执行实例 | 可复用的解决方案模板 |
| **层级** | Goal → Projects → Tasks | **应该是**: Scenario → Projects → Tasks |
| **内容** | 执行中的任务（有状态/分配/进度） | 任务模板（无状态/无分配/无进度） |
| **变化** | 执行中动态增删 | 静态定义，除非主动编辑 |
| **时间** | 事中（问题发生时创建） | 事前（问题发生前定义好） |

**关键**：场景不是一次性裁剪后就不变了，它在执行过程中**持续指导**目标演进——新条件满足时从全集中取出对应 Project/Task。

### 1.2 场景的三段时间维度

```
┌─────────────────────────────────────────────────────────────┐
│ 【阶段一】事前定义                                        │
│  场景 = 全集（PMBOK）                                   │
│  定义所有可能的 Project + Task + 分支 + 条件                │
│  来源：专家纯人工定义 / 知识库推导 / 执行捕捉              │
└─────────────────────────────────────────────────────────────┘
                           │ 实例化
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 【阶段二】实例化时裁剪                                       │
│  根据已知信息从全集中选出"已知必须做"的部分               │
│  mandatory 项目全部创建，conditional 项目条件满足才创建     │
└─────────────────────────────────────────────────────────────┘
                           │ 执行
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 【阶段三】执行时变更                                         │
│  新情况出现 → 条件满足 → 从全集中取出对应 Project/Task    │
│  情况变化 → 某项目不再需要 → 跳过/暂停                      │
│  变更依据是场景全集，不是随意修改                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、数据结构对比

### 2.1 Goal 的数据结构（已实现）

```
Goal
├── 基本信息: id, title, description, status, created_at, ...
├── capability_tags: JSON {business:[], professional:[], technical:[], management:[]}
├── projects: Project[]
│   ├── id, name, description, status, next_step
│   ├── capability_tags: JSON
│   └── tasks: Task[]
│       ├── id, title, description, status, assigned_agent
│       ├── capability_tags: JSON
│       └── 执行状态: todo/in_progress/done/failed
└── 执行相关: traceId, disputes, solutions, iterations
```

### 2.2 Scenario 的现状结构（有问题）

```
Scenario
├── 基本信息: id, name, category, status, version, ...
├── scenario_steps: Step[] ← 扁平列表，没有 Project 概念！
│   ├── id, scenario_id, order, name, agent_type, required_capabilities
│   └── condition_type, condition_data
├── scenario_task_templates: TaskTemplate[]
│   ├── id, scenario_id, phase_name ← 用 phase_name 关联到 Step
│   ├── task_name, task_description, agent_type, required_capabilities
│   └── dependencies, order_in_phase, estimated_hours, priority
├── 缺失:
│   ├── ❌ fullset 列（DB 不存在）
│   ├── ❌ goal_capability_tags 列（DB 不存在）
│   ├── ❌ scenario_projects 表（DB 不存在）
│   └── ❌ scenario_tasks.project_id 关联
└── 多余:
    ├── scenario_steps（应该改为 scenario_projects）
    └── scenario_task_templates（应该保留但关联到 projects）
```

### 2.3 Scenario 应该的结构（设计目标）

```
Scenario
├── 基本信息: id, name, category, status, version, ...
├── fullset: JSON
│   ├── goal_tags: {business:[], professional:[], technical:[], management:[]}
│   └── projects: ProjectTemplate[]
│       ├── name, project_type (mandatory/conditional)
│       ├── condition_type, condition_data
│       ├── capability_tags: JSON
│       ├── next_step: string[]
│       └── tasks: TaskTemplate[]
│           ├── name, description, agent_type
│           ├── required_capabilities: string[]
│           ├── condition_type, condition_data
│           ├── dependencies, order_in_phase
│           └── estimated_hours, priority
├── versions: [{v, date, stats}]
├── source: enum (manual/ai_generated/cognitive_derived/...)
├── trust_level: enum (high/medium/low)
└── 统计:
    ├── total_executions, success_count, failed_count
    ├── success_rate, avg_duration_ms, min_duration_ms, max_duration_ms
    ├── avg_conflicts, avg_step_completion
    └── usage_count
```

---

## 三、页面结构对比

### 3.1 GoalDetail 页面结构（55KB，完整实现）

```
GoalDetail
├── Header: ID + 状态徽章 + 标题 + 描述 + capability_tags
├── 迭代模式选择 (normal / 探索 / 迭代)
├── 激活执行按钮
├── 进度条（x/y 任务已完成）
├── 迭代控制面板（探索/迭代模式）
├── 方案对比卡片网格（探索模式）
├── 任务列表（按 Project 分组）
│   ├── Project 1
│   │   ├── Task A（状态 / 分配给 / 优先级）
│   │   └── Task B
│   └── Project 2
│       └── Task C
├── 迭代历史 Tab
└── 争议面板
```

### 3.2 ScenarioDetail 页面结构（52KB，有问题）

```
ScenarioDetail
├── Header: 标题 + 分类 + 状态徽章
├── Tabs: 基本信息 / 步骤 / 统计
├── 基本信息 Tab
│   ├── 基本信息编辑器（名称/分类/描述/triggers/版本/来源）
│   └── 能力标签（❌ 没有 capability_tags）
├── 步骤 Tab ← 问题在这里
│   ├── StepCard 1
│   │   └── TaskCard 1（靠 phase_name 关联，不是真正的 Project）
│   │   └── TaskCard 2
│   ├── StepCard 2
│   │   └── TaskCard 3
│   └── ...
└── 统计 Tab
    ├── 总执行次数
    ├── 成功率
    └── 平均耗时
```

### 3.3 ScenarioDetail 应该的结构

```
ScenarioDetail
├── Header: ID + 状态徽章 + 标题 + 描述 + fullset 概览
├── "从场景创建目标" 按钮
├── Tabs: 基本信息 / 项目结构 / 统计 / 版本
├── 基本信息 Tab
│   ├── 基本信息编辑器
│   ├── fullset.goal_tags 展示（四维能力需求）
│   ├── 来源 + 可信度 + 版本
│   └── 触发条件（triggers）
├── 项目结构 Tab ← 核心改动
│   ├── Project: 应急响应 (mandatory)
│   │   ├── Task: 启动应急预案 (mandatory)
│   │   └── Task: 通知指挥中心 (mandatory)
│   ├── Project: 泄漏源控制 (conditional ⚠️)
│   │   └── Task: 确认泄漏源 (conditional)
│   ├── Project: 疏散 (conditional ⚠️)
│   │   ├── Task: 疏散北侧 (conditional, wind_direction=north)
│   │   └── Task: 疏散南侧 (conditional, wind_direction=south)
│   └── Project: 善后恢复 (conditional ⚠️)
│       └── Task: 损失评估 (mandatory)
├── 统计 Tab
│   └── 执行指标表格（保持不变）
└── 版本 Tab ← 新增
    ├── 版本历史列表（versions 数组）
    ├── 版本对比（选择两个版本查看差异）
    └── 执行效果关联（哪个版本执行效果好）
```

---

## 四、差距矩阵（逐项分析）

### 4.1 数据结构差距

| # | 差距项 | Goal（已实现） | Scenario（现状） | 应该是什么 | 优先级 |
|---|--------|---------------|-----------------|-----------|--------|
| 1 | **Project 层** | ✅ `projects` 表 | ❌ `scenario_steps` 是扁平列表 | ✅ `scenario_projects` 表 | P0 |
| 2 | **Task 关联** | ✅ `tasks.project_id` → projects | ⚠️ `phase_name` 字符串关联 | ✅ `project_id` FK 关联 | P0 |
| 3 | **fullset 列** | ❌ 不需要 | ❌ DB 不存在 | ✅ JSON 列存储全集 | P0 |
| 4 | **能力标签** | ✅ `capability_tags` JSON | ❌ 无 | ✅ `goal_capability_tags` + 每个 Project/Task 的 `capability_tags` | P0 |
| 5 | **条件分支** | ✅ `next_step` + `condition_type` | ⚠️ Step 有 `condition_type`，Task 无 | ✅ Project 和 Task 都有条件分支 | P1 |
| 6 | **版本管理** | ❌ 没有 | ⚠️ `versions` 列存在但无操作 | ✅ 版本对比 + 反馈回流 | P2 |
| 7 | **场景来源** | ❌ 不需要 | ⚠️ `source` 列存在但无前端入口 | ✅ 来源类型选择器 | P2 |
| 8 | **DAG 可视化** | ✅ `template_dag` 列存在 | ⚠️ `template_dag` 列存在但无 UI | ✅ DAG 图展示 | P2 |

### 4.2 API 差距

| # | 差距项 | 现有 API | 需要什么 | 优先级 |
|---|--------|---------|---------|--------|
| 1 | **场景详情** | `GET /scenarios/:id` 返回 Steps | ✅ 返回 Projects → Tasks | P0 |
| 2 | **场景创建** | `POST /scenarios/` 接受 Steps | ✅ 接受 Projects → Tasks | P0 |
| 3 | **fullset 端点** | ❌ 无 | ✅ `GET/PUT /scenarios/:id/fullset` | P0 |
| 4 | **场景匹配** | ❌ 无 | ✅ 基于 fullset.goal_tags 的推荐 | P1 |
| 5 | **实例化为 Goal** | ❌ 无 | ✅ `POST /scenarios/:id/instantiate` | P1 |
| 6 | **版本对比** | ❌ 无 | ✅ `GET /scenarios/:id/versions/:v1/compare/:v2` | P2 |
| 7 | **场景反馈** | ❌ 无 | ✅ `POST /scenarios/:id/feedback` | P2 |

### 4.3 前端差距

| # | 差距项 | 现状 | 需要什么 | 优先级 |
|---|--------|-----|---------|--------|
| 1 | **项目结构 Tab** | ❌ 只有 Steps 扁平列表 | ✅ 按 Project 分组展示 | P0 |
| 2 | **fullset 展示** | ❌ 无 | ✅ 四维能力需求可视化 | P0 |
| 3 | **条件标记** | ⚠️ 有 ConditionBadge 但只显示在 Task | ✅ Project 和 Task 都有条件标记 | P1 |
| 4 | **版本 Tab** | ❌ 无 | ✅ 版本历史 + 对比 | P2 |
| 5 | **从场景创建 Goal** | ❌ 无 | ✅ 裁剪对话框 + 创建按钮 | P1 |
| 6 | **场景市场页面** | ❌ 无 | ✅ 场景浏览/推荐页面 | P3 |
| 7 | **DAG 图** | ❌ 无 | ✅ 项目依赖关系可视化 | P3 |

### 4.4 执行链路差距

| # | 差距项 | 现状 | 需要什么 | 优先级 |
|---|--------|-----|---------|--------|
| 1 | **traceId 关联** | ❌ 无 | ✅ 场景实例化时生成 traceId | P1 |
| 2 | **执行统计回流** | ❌ 无 | ✅ Goal 完成后更新场景统计数据 | P1 |
| 3 | **高频路径固化** | ❌ 无 | ✅ 执行数据驱动场景优化建议 | P2 |
| 4 | **动态条件评估** | ❌ 无 | ✅ 执行中条件触发 Project/Task 创建 | P1 |

---

## 五、完成度评估

### 5.1 按模块评估

| 模块 | 完成度 | 说明 |
|------|--------|------|
| 场景 CRUD（列表/详情/创建/编辑/删除） | **75%** | 基础功能有，但结构不对 |
| 场景列表页（搜索/过滤/排序/分页） | **90%** | 星标收藏也有 |
| 场景详情页 Tab 结构 | **60%** | Tab 有，但内容不对 |
| 场景条件编辑器 | **80%** | ConditionDataEditor 有 |
| **Project 层结构** | **0%** | 核心缺失 |
| **fullset + 能力标签** | **0%** | DB 列不存在 |
| 场景实例化为 Goal | **0%** | 无入口 |
| 场景匹配引擎 | **0%** | 无实现 |
| 场景版本管理 | **10%** | 列存在但无操作 |
| 全链路追踪（traceId） | **0%** | 无关联 |
| 执行统计回流 | **0%** | 无实现 |
| 场景市场页面 | **0%** | 无实现 |
| DAG 可视化 | **0%** | 列存在但无 UI |
| 场景反馈回流 | **0%** | API 有但前端无入口 |

**整体完成度: ~25%**

### 5.2 优先级分布

| 优先级 | 数量 | 核心项 |
|--------|------|--------|
| P0（阻塞性） | 5 | Project 层 / fullset / 能力标签 / 场景详情 API / 场景创建 API |
| P1（重要） | 6 | 场景实例化 / 匹配引擎 / traceId / 条件评估 / 执行回流 / fullset API |
| P2（改进） | 5 | 版本管理 / DAG / 来源 / 反馈 / 高频路径 |
| P3（锦上添花） | 2 | 场景市场 / DAG 可视化 |

---

## 六、关键发现

### 6.1 最严重的三个问题

#### P0-1: Scenario 没有 Project 层（数据结构错误）

**现状**：
- `scenario_steps` 表是扁平列表（id / scenario_id / order / name / agent_type / required_capabilities / condition_type / condition_data）
- `scenario_task_templates` 表通过 `phase_name` 字符串关联到 Step，不是 FK
- 前端 ScenarioDetail 把所有 Steps 和 Tasks 扁平展示

**应该**：
```
Scenario → scenario_projects → scenario_task_templates
```

**后果**：
1. 无法按 Project 做条件判断（conditional 项目的概念不存在）
2. 实例化时无法按 Project 裁剪
3. 与 Goal 结构不对齐，无法复用 GoalDetail 的页面模式

**修复**：新增 `scenario_projects` 表，将 `scenario_steps` 改造为 Project 级别，或新建表后迁移数据。

#### P0-2: 没有 fullset 列（场景无法参与能力匹配）

**现状**：
- DB 的 `scenarios` 表没有 `fullset` 列
- `scenario_task_templates` 只有 `required_capabilities`（字符串数组），不是四维标签
- 场景无法被驾驭中心用于匹配

**应该**：
```sql
ALTER TABLE scenarios ADD COLUMN fullset TEXT DEFAULT '{}';
ALTER TABLE scenarios ADD COLUMN goal_capability_tags TEXT DEFAULT '{}';
ALTER TABLE scenario_projects ADD COLUMN capability_tags TEXT DEFAULT '{}';
```

**后果**：场景无法描述能力需求，无法参与智能体匹配。

#### P0-3: ScenarioDetail 页面结构不对

**现状**：按 Steps 扁平展示

**应该**：按 Projects 分组展示 Tasks（参照 GoalDetail 的任务列表模式）

---

### 6.2 不需要做的事情（场景 ≠ Goal 的部分）

| Goal 有 | 场景不需要 | 原因 |
|---------|-----------|------|
| 进度条 | ❌ 不需要 | 场景是模板，没有执行进度 |
| 迭代控制面板 | ❌ 不需要 | 场景不迭代 |
| 方案对比 | ❌ 不需要 | 场景是蓝图，没有方案 |
| 任务执行状态 | ❌ 不需要 | Task 是模板，没有 todo/in_progress/done |
| Agent 分配 | ❌ 不需要 | 只有 agent_type，没有 assigned_agent |
| 争议面板 | ❌ 不需要 | 模板无争议 |
| 迭代历史 | ❌ 不需要 | 场景有版本历史，不是迭代历史 |

---

## 七、实施优先级建议

### Phase 1（P0，必须先做）
1. **DB 迁移**：新增 `scenario_projects` 表 + `fullset` 列 + 数据迁移
2. **API 重构**：`GET/POST/PUT /scenarios` 返回 Projects 结构
3. **前端重构**：ScenarioDetail 按 Project 分组展示

### Phase 2（P1，紧随其后）
4. **fullset 端点**：`GET/PUT /scenarios/:id/fullset`
5. **场景实例化**：从场景创建 Goal 入口
6. **匹配引擎**：基于 fullset.goal_tags 的场景推荐

### Phase 3（P2，持续改进）
7. **版本管理**：版本历史 + 对比
8. **全链路追踪**：traceId 关联场景实例化
9. **执行回流**：Goal 完成后更新场景统计

### Phase 4（P3，锦上添花）
10. **场景市场**：场景浏览/推荐页面
11. **DAG 可视化**：项目依赖关系图

---

## 八、风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 迁移数据丢失 | 高 | 低 | scenario_steps 当前为空，迁移无风险 |
| 旧 API 不兼容 | 中 | 高 | 保留旧 Steps 端点作为兼容层 |
| 前端重构工作量大 | 中 | 高 | 先改核心页面，列表页后续迭代 |
| 用户期望过高 | 低 | 中 | 明确本次只做结构对齐，匹配引擎等后续做 |
