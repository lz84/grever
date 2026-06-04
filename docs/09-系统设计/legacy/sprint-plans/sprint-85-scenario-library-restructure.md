# Sprint 85: 场景库结构重构 — Scenario 对齐 Goal 层级

> 日期: 2026-05-20  
> 优先级: P0  
> 核心理念: 场景 = 目标的结构（Project→Task），只是没有执行部分

---

## 一、问题背景

### 1.1 核心差距

| 维度 | Goal（已实现） | Scenario（现状） | 差距 |
|------|---------------|-----------------|------|
| 层级 | Goal → Projects → Tasks | Scenario → Steps（扁平） + Tasks | ❌ 缺 Project 层 |
| 能力标签 | capability_tags (JSON) | 无 fullset 列 | ❌ 缺失 |
| 详情页 | 按 Project 分组展示 | 扁平 Steps 列表 | ❌ 结构不对 |
| 实例化 | 从场景创建 Goal | 无入口 | ❌ 断裂 |
| 执行反馈 | traceId 追踪 | 无关联 | ❌ 缺失 |

**关键洞察**：用户说"场景在我想象里跟定义目标差不多，展现场景跟展现目标也差不多，只是场景不展示目标的执行部分"。

### 1.2 目标结构对标

```
Goal (目标)                        Scenario (场景)
├── 基本信息                        ├── 基本信息 ✅ 有
├── capability_tags                 ├── fullset / capability_tags ❌ 缺失
├── Projects (按组展示)              ├── Projects ❌ 缺失（只有 Steps 扁平）
│   └── Tasks (状态/分配)           │   └── Tasks (模板，无执行状态)
├── 进度条 ✅                       ├── ❌ 不需要（模板无进度）
├── 迭代控制面板 ✅                  ├── ❌ 不需要（模板不迭代）
├── 方案对比 ✅                      ├── ❌ 不需要（模板无方案）
├── 任务列表 (执行态)                ├── 任务模板（定义态）✅ 部分
├── 迭代历史 ✅                      ├── 版本历史 ❌ 缺失
└── 争议面板 ✅                      └── ❌ 不需要（模板无争议）
```

**结论**：Scenario 需要补的核心是 **Project 层 + fullset + 版本管理**，不需要的都是执行态功能。

---

## 二、迭代任务分解

### Sprint 85a: DB 结构重构（后端 P0）

**Done Criteria**:
- [ ] 迁移脚本执行成功，零数据丢失
- [ ] `scenario_projects` 表有数据（从 scenario_steps 迁移）
- [ ] `scenario_tasks.project_id` 正确关联
- [ ] 旧 `scenario_steps` 表已删除或标记 deprecated
- [ ] `npx tsc --noEmit` 0 errors
- [ ] `pytest` 通过

#### Task 85a-1: 新增 029 迁移脚本

**依赖**: `depends_on=[]`

**内容**:

```sql
-- 029_scenario_restructure.sql

-- 1. 创建 scenario_projects 表（替代 scenario_steps）
CREATE TABLE scenario_projects (
    id VARCHAR(36) PRIMARY KEY,
    scenario_id VARCHAR(36) NOT NULL REFERENCES scenarios(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    project_type VARCHAR(20) DEFAULT 'mandatory',  -- mandatory/conditional
    condition_type VARCHAR(20) DEFAULT 'none',     -- none/auto_eval/human_decision/human_input
    condition_data TEXT,                           -- JSON
    next_step TEXT,                                -- JSON array of project IDs
    capability_tags TEXT,                          -- JSON object: {business:[], professional:[], technical:[], management:[]}
    order_index INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. scenarios 表新增 fullset 列
ALTER TABLE scenarios ADD COLUMN fullset TEXT DEFAULT '{}';

-- 3. scenarios 表新增 capability_tags 列（Goal 级标签）
ALTER TABLE scenarios ADD COLUMN goal_capability_tags TEXT DEFAULT '{}';

-- 4. scenario_task_templates 新增 project_id 列
ALTER TABLE scenario_task_templates ADD COLUMN project_id VARCHAR(36) REFERENCES scenario_projects(id);

-- 5. 数据迁移：scenario_steps → scenario_projects
INSERT INTO scenario_projects (id, scenario_id, name, description, order_index, created_at, updated_at)
SELECT 
    'sp-' || substr(id, 7, 24),
    scenario_id,
    name,
    COALESCE(condition_data, ''),
    order_index,
    created_at,
    updated_at
FROM scenario_steps;

-- 6. 数据迁移：scenario_task_templates.project_id 关联
UPDATE scenario_task_templates SET project_id = (
    SELECT sp.id FROM scenario_projects sp
    WHERE sp.scenario_id = scenario_task_templates.scenario_id
    AND sp.name = scenario_task_templates.phase_name
    LIMIT 1
);
```

**验收命令**:
```bash
cd packages/server
python -m reins.migration.run_migration  # 假设的迁移执行脚本
# 验证
sqlite3 data/reins.db "SELECT COUNT(*) FROM scenario_projects"
sqlite3 data/reins.db "SELECT COUNT(*) FROM scenario_task_templates WHERE project_id IS NOT NULL"
```

**文件**:
- `packages/server/src/reins/persistence/migrations/029_scenario_restructure.sql`
- `packages/server/src/reins/persistence/migrations/029_scenario_restructure.down.sql`

#### Task 85a-2: 更新 ORM 模型

**依赖**: `depends_on=["85a-1"]`

**内容**:
- `scenario.py`: 新增 `ScenarioProject` ORM 模型
- `scenario_task.py`: 新增 `project_id` 关系
- Pydantic models: 更新 `ScenarioResponse`、`ScenarioSummary`、`ScenarioProjectResponse`
- `scenarios_crud.py`: 更新 `get_scenario` 端点，返回 Projects 结构

**验收**:
```bash
curl http://127.0.0.1:8097/api/v1/scenarios/scenario-chemical-001
# 返回结构应包含 projects 数组，每个 project 有 tasks 数组
```

**文件**:
- `packages/server/src/reins/models/scenario.py` (修改)
- `packages/server/src/reins/models/scenario_project.py` (新建)
- `packages/server/src/reins/api/scenarios_crud.py` (修改)

---

### Sprint 85b: API 层重构（后端 P0）

**Done Criteria**:
- [ ] GET `/scenarios/:id` 返回 Projects 结构（不是 Steps）
- [ ] POST `/scenarios` 接受 Projects 结构创建
- [ ] PUT `/scenarios/:id` 支持 Projects 更新
- [ ] `npx tsc --noEmit` 0 errors
- [ ] API 验证通过（见 Acceptance Criteria）

#### Task 85b-1: 场景 CRUD 端点重构

**依赖**: `depends_on=["85a-2"]`

**内容**:
- `GET /scenarios/` → 返回 ScenarioSummary（包含 project_count）
- `GET /scenarios/{id}` → 返回 ScenarioResponse（含 projects → tasks 层级）
- `POST /scenarios/` → 接受 `projects[]` 创建场景
- `PUT /scenarios/{id}` → 支持 Projects 更新
- `DELETE /scenarios/{id}` → 级联删除 Projects + Tasks

**请求体结构**:
```json
{
  "name": "化工厂危化品泄漏应急预案",
  "category": "chemical",
  "description": "...",
  "fullset": {
    "goal_tags": { "business": [...], "professional": [...], ... },
    "projects": [
      {
        "name": "应急响应",
        "project_type": "mandatory",
        "capability_tags": { ... },
        "tasks": [
          { "name": "启动应急预案", "agent_type": "executor", ... }
        ]
      },
      {
        "name": "疏散",
        "project_type": "conditional",
        "condition_type": "human_decision",
        "condition_data": { ... },
        "capability_tags": { ... },
        "tasks": [...]
      }
    ]
  }
}
```

**验收**:
```bash
# 1. 创建场景
curl -X POST http://127.0.0.1:8097/api/v1/scenarios \
  -H 'Content-Type: application/json' \
  -d '{"name":"测试场景","category":"general","projects":[{"name":"Phase 1","tasks":[{"name":"Task 1"}]}]}'
# 返回 201 + ScenarioResponse

# 2. 获取场景详情
curl http://127.0.0.1:8097/api/v1/scenarios/{id}
# 返回 200 + projects 数组，每个 project 有 tasks 数组

# 3. 更新场景
curl -X PUT http://127.0.0.1:8097/api/v1/scenarios/{id} \
  -H 'Content-Type: application/json' \
  -d '{"projects":[{"name":"Phase 2","tasks":[{"name":"Task A"}]}]}'
# 返回 200 + 更新后的结构
```

**文件**:
- `packages/server/src/reins/api/scenarios_crud.py` (大幅修改)
- `packages/server/src/reins/api/scenario_models.py` (新增 Pydantic models)

#### Task 85b-2: fullset 专用端点

**依赖**: `depends_on=["85b-1"]`

**内容**:
- `GET /scenarios/{id}/fullset` → 返回场景的 fullset 结构
- `PUT /scenarios/{id}/fullset` → 更新 fullset（单独端点，避免全场景更新）
- 用于场景匹配引擎读取 fullset.goal_tags

**验收**:
```bash
curl http://127.0.0.1:8097/api/v1/scenarios/{id}/fullset
# 返回 { goal_tags: {...}, projects: [...] }
```

**文件**:
- `packages/server/src/reins/api/scenarios_fullset.py` (新建)

---

### Sprint 85c: 前端 ScenarioDetail 重构（前端 P0）

**Done Criteria**:
- [ ] ScenarioDetail 页面按 Project 分组展示 Tasks
- [ ] 基本信息 Tab 显示 fullset 概览
- [ ] 项目结构 Tab 显示 Project→Task 层级（不是 Steps→Task）
- [ ] 统计 Tab 保持不变
- [ ] 页面不白屏，数据正确渲染
- [ ] TypeScript 编译 0 errors

#### Task 85c-1: ScenarioDetail 页面重构

**依赖**: `depends_on=["85b-1"]`

**内容**:
- Tab 结构：基本信息 / 项目结构 / 统计 / 版本（新增）
- **基本信息 Tab**: 名称/分类/描述/触发条件/来源/fullset 概览
- **项目结构 Tab**: 按 Project 分组展示 Tasks，支持:
  - 展开/折叠 Project
  - 查看 Project 的 condition_type（conditional 项目有标记）
  - 查看 Task 模板详情（名称/描述/agent_type/优先级/条件）
- **版本 Tab**: 显示版本历史（versions 数组），支持版本对比
- **统计 Tab**: 保持不变

**参照 GoalDetail 结构**:
```
ScenarioDetail
├── Header: ID + 状态徽章 + 标题 + 描述
├── Tabs: 基本信息 / 项目结构 / 统计 / 版本
├── 基本信息 Tab
│   ├── 基本信息编辑器
│   ├── fullset 概览（goal_tags 展示）
│   └── 来源 + 版本 + 可信度
├── 项目结构 Tab
│   ├── Project: 应急响应 (mandatory)
│   │   ├── Task: 启动应急预案
│   │   └── Task: 通知指挥中心
│   ├── Project: 疏散 (conditional ⚠️)
│   │   └── Task: 疏散人员
│   └── Project: 善后恢复 (conditional ⚠️)
│       └── Task: 损失评估
├── 统计 Tab
│   └── 执行指标表格
└── 版本 Tab
    └── 版本历史列表
```

**文件**:
- `packages/ui/src/pages/ScenarioDetail.tsx` (大幅重写)
- `packages/ui/src/utils/scenariosApi.ts` (更新类型定义)
- `packages/ui/src/components/ScenarioProjectCard.tsx` (新建)
- `packages/ui/src/components/ScenarioTaskCard.tsx` (新建)
- `packages/ui/src/components/ScenarioFullsetView.tsx` (新建)

#### Task 85c-2: ScenarioList 页面更新

**依赖**: `depends_on=["85b-1"]`

**内容**:
- 列表显示 `project_count`（场景包含的项目数）
- 列表显示 `capability_tags` 预览（从 fullset.goal_tags 提取）
- 筛选条件增加 `has_projects`（是否有 Project 定义）

**文件**:
- `packages/ui/src/pages/ScenarioList.tsx` (修改)

---

### Sprint 85d: 场景实例化入口（P1）

**Done Criteria**:
- [ ] ScenarioDetail 页面有"从场景创建 Goal"按钮
- [ ] 点击后弹出裁剪对话框
- [ ] 用户选择 mandatory + 已知条件满足的 Projects
- [ ] 创建 Goal 后跳转到 Goal 详情页
- [ ] 端到端流程跑通

#### Task 85d-1: 从场景创建 Goal

**依赖**: `depends_on=["85c-1"]`

**内容**:
- ScenarioDetail 页面顶部增加"从场景创建目标"按钮
- 弹出对话框：
  - 显示场景的所有 Projects
  - mandatory 项目默认勾选
  - conditional 项目根据条件判断是否可选
  - 用户可手动勾选/取消
  - 输入 Goal 标题和描述
- 调用 `POST /goals` 创建目标
- 创建的 Goal 继承场景的 Project → Task 结构

**文件**:
- `packages/ui/src/components/InstantiateGoalDialog.tsx` (新建)
- `packages/ui/src/pages/ScenarioDetail.tsx` (修改)
- `packages/server/src/reins/api/goals_crud.py` (可能需要新增场景实例化端点)

---

## 三、依赖关系图

```
85a-1 (DB 迁移)
   ↓
85a-2 (ORM 模型)
   ↓
85b-1 (CRUD API)
   ├→ 85b-2 (fullset API)
   ├→ 85c-1 (ScenarioDetail)
   │      ↓
   │   85c-2 (ScenarioList)
   │      ↓
   └→ 85d-1 (实例化入口)
```

## 四、实施顺序

```
Phase 1: DB + ORM (85a)
  ↓
Phase 2: API 层 (85b)
  ↓
Phase 3: 前端页面 (85c)
  ↓
Phase 4: 实例化入口 (85d)
```

## 五、风险与注意事项

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 迁移数据丢失 | 高 | 迁移前备份 DB，迁移后验证数据完整性 |
| 旧 API 不兼容 | 中 | 保留旧 Steps 端点作为兼容层，标注 deprecated |
| 前端重构工作量大 | 中 | 先改 ScenarioDetail 核心页面，列表页后续迭代 |
| scenario_steps 有数据 | 低 | 当前 scenario_steps 表为空，迁移无风险 |

## 六、验收四板斧

每个 Task 完成后必须执行：

| 步骤 | 验证内容 | 命令/方法 | 通过标准 |
|------|----------|-----------|----------|
| 1. 编译验证 | TS 编译 | `npx tsc --noEmit` | 0 errors |
| 2. API 验证 | 关键端点 | curl | 200 + 正确 JSON 结构 |
| 3. 数据验证 | DB 关键字段 | `PRAGMA table_info` + `SELECT` | 关键字段有值，关联正确 |
| 4. 页面验证 | 前端渲染 | 浏览器访问 | 不白屏，Project→Task 层级正确显示 |

---

## 七、文件变更清单

### 新建文件
```
packages/server/src/reins/persistence/migrations/029_scenario_restructure.sql
packages/server/src/reins/persistence/migrations/029_scenario_restructure.down.sql
packages/server/src/reins/models/scenario_project.py
packages/server/src/reins/api/scenarios_fullset.py
packages/ui/src/components/ScenarioProjectCard.tsx
packages/ui/src/components/ScenarioTaskCard.tsx
packages/ui/src/components/ScenarioFullsetView.tsx
packages/ui/src/components/InstantiateGoalDialog.tsx
```

### 修改文件
```
packages/server/src/reins/models/scenario.py
packages/server/src/reins/api/scenarios_crud.py
packages/server/src/reins/api/scenario_models.py
packages/ui/src/pages/ScenarioDetail.tsx
packages/ui/src/pages/ScenarioList.tsx
packages/ui/src/utils/scenariosApi.ts
```

### 删除文件（标记 deprecated）
```
无（保留 scenario_steps 表作为历史兼容）
```
