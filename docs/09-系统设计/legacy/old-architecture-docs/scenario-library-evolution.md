# 场景库演进方案 — 场景来源与自定义场景构建

> **日期**: 2026-05-01
> **状态**: 设计稿，待评审
> **讨论参与者**: 用户、刚子

---

## 一、核心问题

当前场景库（scenarios）存在两个关键断裂：

1. **场景来源单一** — 仅支持 LLM 自动生成（`llm_generated`），缺少从认知库沉淀和执行经验中提炼场景的能力
2. **自定义场景入口薄弱** — 仅有基础 CRUD（`POST /scenarios/`），没有引导式创建流程，无法定义完整的项目流程和任务模板

---

## 二、场景来源双通道设计

### 总体架构

```
┌──────────────────────┐
│   认知库（历史沉淀）    │  facts / patterns / lessons
│   grasp/cognitive     │  执行后提炼的知识
└──────────┬───────────┘
           │ 通道一：事后提炼
           ↓
    ┌──────────────┐     实例化     ┌──────────────────┐
    │   场景库      │ ──────────→  │  新目标 / 新项目    │
    │  scenarios    │              │                  │
    └──────┬───────┘              └──────────────────┘
           ↑
           │ 通道二：实时捕捉
           │
┌──────────┴───────────┐
│ 正在执行的目标/项目     │  活跃的 workflow 实例
│  goals / projects     │  被验证有效的执行路径
└──────────────────────┘
```

### 通道一：认知库 → 场景（事后提炼）

**触发时机**：
- 目标/项目执行完成后，认知库积累了新的 facts/patterns/lessons
- 多个认知条目具有相同领域标签 → 自动聚合 → 建议"是否保存为场景？"

**流程**：
```
执行完成 → 认知注入（grasp）→ 同领域认知聚合 → LLM 总结场景模板 → 用户确认 → 存入场景库
```

**实现要点**：
- 新增端点：`POST /api/v1/scenarios/derive-from-cognitions`
- 参数：`{ domain: "化工应急", cognition_ids: ["cog-xxx", "cog-yyy"] }`
- 逻辑：
  1. 读取认知库中指定领域/ID 的认知条目
  2. 让 LLM 总结出一个场景模板（名称、分类、描述、步骤、task 模板）
  3. 返回预览，用户确认后写入场景库
  4. 建立 `scenario_cognitions` 关联表记录来源

**数据库扩展**：

```sql
-- 场景-认知关联表
CREATE TABLE scenario_cognitions (
    id TEXT PRIMARY KEY,
    scenario_id TEXT REFERENCES scenarios(id),
    cognition_id TEXT,
    relevance_score REAL,
    created_at TEXT
);
```

**场景来源枚举扩展**：

| source 值 | 含义 |
|-----------|------|
| `cognitive_derived` | 从认知库自动生成 |
| `manual` | 用户手动创建 |
| `llm_generated` | LLM 自动生成（已有，基于目标标题） |
| `execution_derived` | 从执行中的目标/项目提炼 |
| `template` | 从模板复制 |
| `evolved` | 从反馈自动进化 |

---

### 通道二：正在执行的目标/项目 → 场景（实时捕捉）

**触发时机**：
- 用户发现某个正在执行的目标/项目的 workflow 路径效果很好
- 希望将该执行路径保存为可复用的场景模板
- 下次遇到类似目标时可直接实例化

**流程**：
```
执行中的目标/项目 → 用户点击"保存为场景" → 打包 workflow DAG + tasks → 场景预览 → 编辑完善 → 存入场景库
```

**实现要点**：
- 目标详情页 / 项目详情页增加"保存为场景"按钮
- 后端端点：`POST /api/v1/scenarios/from-execution/{goal_id|project_id}`
- 逻辑：
  1. 读取目标的 workflow DAG（`workflows` 表）
  2. 读取关联的 projects / tasks
  3. 将 workflow DAG 转换为 `template_dag` 格式
  4. 将 tasks 聚合为 task_templates（按 project 分组）
  5. 生成场景预览（名称、分类、描述可编辑）
  6. 用户确认后写入场景库，source = `execution_derived`

**前端入口**：
- `GoalDetail.tsx`：顶部操作栏增加"保存为场景"按钮
- `ProjectDetail.tsx`：同位置增加
- 点击后弹出编辑表单，允许修改名称/分类/描述后再保存

---

## 三、自定义场景构建器设计

### 现有问题

当前 `POST /api/v1/scenarios/` 只接受基础字段：
```json
{
  "name": "场景名称",
  "category": "flood",
  "description": "描述",
  "scenario_desc": "详细场景描述",
  "triggers": ["触发条件"],
  "steps": [{"order": 1, "name": "步骤1", "agent_type": "executor"}]
}
```

**缺失能力**：
- ❌ 无法定义项目级别的流程（phases）
- ❌ 无法为每个 phase 定义任务模板（task_templates）
- ❌ 无法关联认知条目
- ❌ 无引导式创建流程（纯 API，无前端交互）

### 自定义场景创建端点设计

```
POST /api/v1/scenarios/custom-create
```

**请求体**：

```json
{
  "basic": {
    "name": "城市内涝应急响应",
    "category": "flood",
    "description": "一句话描述场景用途",
    "scenario_desc": "详细场景描述，包含目标、步骤、注意事项",
    "source_type": "manual",
    "cognition_refs": ["cog-xxx", "cog-yyy"],
    "triggers": ["水位超过警戒线", "暴雨红色预警"]
  },
  "project_workflow": {
    "phases": [
      {
        "name": "应急响应",
        "order": 1,
        "description": "启动应急预案，通知相关部门",
        "dependencies": []
      },
      {
        "name": "现场处置",
        "order": 2,
        "description": "现场救援和疏散",
        "dependencies": ["应急响应"]
      },
      {
        "name": "善后恢复",
        "order": 3,
        "description": "灾后重建和损失评估",
        "dependencies": ["现场处置"]
      }
    ]
  },
  "task_templates": [
    {
      "phase": "应急响应",
      "title": "水位监测",
      "description": "监测关键水位点并上报",
      "agent_requirements": ["监控能力", "数据分析"],
      "priority": "high",
      "estimated_hours": 2
    },
    {
      "phase": "应急响应",
      "title": "预警发布",
      "description": "向受影响区域发布预警信息",
      "agent_requirements": ["通信能力"],
      "priority": "critical",
      "estimated_hours": 1
    },
    {
      "phase": "现场处置",
      "title": "人员疏散",
      "description": "组织低洼区域人员疏散",
      "agent_requirements": ["协调能力", "人力资源"],
      "priority": "critical",
      "estimated_hours": 4
    }
  ]
}
```

**后端自动生成**：
1. 从 `project_workflow.phases` 生成 `template_dag`（nodes + edges）
2. 从 `task_templates` 生成场景级别的任务模板列表
3. 从所有 task 的 `agent_requirements` 汇总为 `agent_requirements`
4. 建立与认知库的关联（`scenario_cognitions` 表）
5. `source` 自动标记为 `manual` 或 `cognitive_derived`

### 数据库扩展

```sql
-- 场景任务模板表
CREATE TABLE scenario_task_templates (
    id TEXT PRIMARY KEY,
    scenario_id TEXT REFERENCES scenarios(id),
    phase_name TEXT,
    title TEXT NOT NULL,
    description TEXT,
    agent_requirements TEXT,    -- JSON array
    priority TEXT DEFAULT 'medium',
    estimated_hours REAL,
    "order" INTEGER,
    created_at TEXT
);
```

### 前端：场景编辑器 UI

三个 Tab 的创建流程：

| Tab | 内容 |
|-----|------|
| **基本信息** | 名称/分类/描述/触发条件/来源类型 |
| **项目流程** | 拖拽式 DAG 编辑器（复用现有 WorkflowDiagram） |
| **任务模板** | 为每个 phase 定义可复用的任务模板 |

**入口位置**：
- 场景库列表页 → "创建场景"按钮
- 目标详情页 → "保存为场景"按钮（通道二）
- 项目详情页 → "保存为场景"按钮（通道二）

---

## 四、优先级与实施计划

| 优先级 | 内容 | 预估工作量 | 依赖 |
|--------|------|-----------|------|
| **P0** | "保存为场景"功能（通道二） | 1 天 | 现有 workflow DAG 已完整 |
| **P0** | 自定义场景创建 API | 1 天 | 数据库扩展 |
| **P1** | 认知→场景 LLM 管道（通道一） | 1.5 天 | grasp 模块数据可访问 |
| **P1** | 场景来源枚举扩展 + 关联表 | 0.5 天 | 独立 |
| **P2** | 前端场景编辑器 | 2 天 | P0 API 完成 |
| **P2** | 场景-认知关联 UI | 1 天 | P1 完成 |

**建议 Sprint 顺序**：
1. 先做通道二（"保存为场景"）— 用户最直观的价值，立即可用
2. 再做自定义场景 API — 补全创建能力
3. 最后做通道一（认知→场景）— 需要 grasp 数据积累到一定量才有价值

---

## 五、待确认事项

1. **认知派生场景的交互方式**：全自动（LLM 读取认知直接生成）还是半自动（用户选择认知条目 + 手动编辑确认）？
2. **任务模板的粒度**：仅 title+description 还是需要完整的 acceptance criteria、sub-tasks、依赖关系？
3. **项目流程定义**：当前 `workflow_step` 只支持线性流程，是否需要支持并行节点 / 条件分支（if-else）？
4. **场景审批流程**：从执行中提炼的场景是否需要审核才能进入场景库？还是直接保存为 draft？

---

*文档结束 — 待用户确认后进入 Sprint 规划*
