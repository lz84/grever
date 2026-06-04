# 能力标签体系设计文档

> 2026-05-18 · 讨论稿 · Nexus 系统重构

---

## 1. 设计目标

建立一套**通用的能力标签匹配体系**，使 Goal-Project-Task-Scenario-Agent 五类实体使用统一的能力描述语言，实现自动化的智能体匹配。

### 核心原则

1. **统一字段名** — 所有实体用同一个字段名描述能力，零映射、零别名
2. **行业无关** — 标签值由用户/行业定义，匹配引擎不关心标签内容
3. **自动推断** — 标签不仅手动配置，更要通过 Agent 运行行为自动标注和更新
4. **多维度 + 权重** — 能力不是有无问题，是置信度问题

---

## 2. 统一字段规范

### 2.1 字段名

**所有实体统一使用 `capability_tags`**

| 实体 | 原字段 | 新字段 | 类型 | 说明 |
|------|--------|--------|------|------|
| **Agent** | `capabilities` (JSON []) | `capability_tags` | JSON object | 多维标签 + 权重 |
| **Goal** | 无 | `capability_tags` | JSON object | 多维标签（引用场景的子集） |
| **Project** | 无 | `capability_tags` | JSON object | 多维标签 |
| **Task** | `category` (String) | `capability_tags` | JSON object | 多维标签（替换 category） |
| **Scenario** | `agent_requirements` (JSON) | `fullset` | JSON object | 场景全集标签 |

### 2.2 数据结构

```json
{
  "business": ["emergency_response", "rescue_coordination"],
  "professional": ["incident_command", "risk_assessment", "report_writing"],
  "technical": ["python", "shell_scripting"],
  "management": ["coordination", "task_dispatch", "grasp_read", "grasp_write"]
}
```

**为什么用 object 而不是 array**：
- 按维度分类，匹配时可以跨维度取并集
- 支持不同维度独立管理权重
- 查询时可以按维度过滤（如"找有协调能力的 Agent"只看 management）

---

## 3. 四个维度定义

### 3.1 业务能力（business）

**含义**：Agent 在特定业务领域的经验。回答"Agent 懂不懂这个行业？"

**标签来源**：
- 场景分配历史（Agent 在哪些场景中执行过任务）
- Goal/Project 的业务类型
- 用户手动标注

**示例标签**（应急响应行业）：
```json
"business": ["emergency_response", "fire_fighting", "rescue_coordination", "evacuation_planning"]
```

**示例标签**（软件开发行业）：
```json
"business": ["software_development", "web_application", "mobile_app", "data_pipeline"]
```

### 3.2 专业能力（professional）

**含义**：Agent 在专业领域的技能。回答"Agent 能做什么专业工作？"

**标签来源**：
- 产出物类型分析（写过报告 → `report_writing`，画过架构图 → `architecture_design`）
- 解决方案评分（高质量 → 标签权重增加）
- 任务类别映射

**示例标签**：
```json
"professional": ["api_design", "database_optimization", "incident_command", "risk_assessment", "report_writing"]
```

### 3.3 技术能力（technical）

**含义**：Agent 使用的技术栈。回答"Agent 用什么工具/语言/框架？"

**标签来源**：
- 工作区文件特征（`.py` 文件多 → `python`，`package.json` → `nodejs`）
- 任务执行结果中的技术栈
- 代码扫描（imports、依赖声明）

**示例标签**：
```json
"technical": ["python", "fastapi", "postgresql", "docker", "typescript", "react"]
```

### 3.4 管理能力（management）

**含义**：Agent 的系统级能力。回答"Agent 会不会用 Nexus 系统？"

**标签来源**：
- 系统调用行为（调 API → `task_dispatch`，连 Grasp → `grasp_read`/`grasp_write`）
- 角色行为（作为 verifier → `coordination`，参与分解 → `task_decomposition`）
- **自动推断，不手动配置**

**示例标签**：
```json
"management": ["coordination", "task_dispatch", "grasp_read", "grasp_write", "task_decomposition"]
```

---

## 4. 自动标注机制

### 4.1 三层模型

```
┌─────────────────┐
│  初始标签层      │  ← 系统启动时读取手动配置
│  (seed tags)    │
├─────────────────┤
│  观察标签层      │  ← Agent 每次执行任务时实时采集
│  (observed tags)│
├─────────────────┤
│  推断标签层      │  ← 定期聚合计算，生成最终 capability_tags
│  (inferred tags)│
└─────────────────┘
```

### 4.2 观察信号采集

| 信号 | 触发时机 | 推断维度 | 推断标签 |
|------|----------|----------|----------|
| Agent 执行代码任务 | task_completed | technical | 扫描代码文件 → `python`, `react` 等 |
| Agent 产出文档 | task_completed | professional | 分析文档类型 → `report_writing`, `api_design` |
| Agent 被分配为 verifier | task_assigned | management | `coordination` |
| Agent 调用 Nexus API | API 调用日志 | management | `task_dispatch` |
| Agent 读写 Grasp | Grasp 调用日志 | management | `grasp_read`, `grasp_write` |
| Agent 参与任务分解 | decompose API | management | `task_decomposition` |
| Agent 完成某业务场景任务 | task_completed + scenario_id | business | 场景的业务标签 → Agent 的业务标签 |
| Agent 解决争议 | dispute_resolved | professional | `conflict_resolution` |

### 4.3 权重衰减模型

每个标签附带一个 **置信度权重** (0.0 ~ 1.0)：

```
初始权重：
  - 手动配置：1.0（最高置信度）
  - 首次观察到：0.3（低置信度）
  
更新规则（每次调度 tick 或每日计算）：
  - 观察到新证据：weight = min(1.0, weight + 0.1)
  - 未观察到（过期）：weight = max(0.0, weight - 0.05)
  - 过期阈值：
    - technical: 30 天未用 → 权重降至 0
    - professional: 60 天未用 → 权重降至 0
    - business: 90 天未用 → 权重降至 0
    - management: 持续有效（不会过期，除非 Agent 下线）
```

**为什么不同维度不同过期时间**：
- 技术栈更新快（30 天没用可能已经换了）
- 专业能力中等（60 天）
- 业务领域相对稳定（90 天）
- 管理能力是系统功能，不会"过期"

### 4.4 数据结构（Agent 侧）

```json
{
  "agent_id": "fefd19b0-...",
  "name": "刚子",
  "capability_tags": {
    "business": ["emergency_response", "rescue_coordination"],
    "professional": ["incident_command", "risk_assessment"],
    "technical": ["python", "shell_scripting"],
    "management": ["coordination", "task_dispatch", "grasp_read", "grasp_write"]
  },
  "tag_weights": {
    "emergency_response": 0.95,
    "rescue_coordination": 0.85,
    "incident_command": 0.90,
    "risk_assessment": 0.70,
    "python": 0.60,
    "shell_scripting": 0.45,
    "coordination": 0.98,
    "task_dispatch": 0.92,
    "grasp_read": 0.88,
    "grasp_write": 0.75
  },
  "last_tag_update": "2026-05-18T14:00:00Z"
}
```

---

## 5. 匹配引擎设计

### 5.1 输入输出

```
输入：
  - 需求方 (Goal/Project/Task) 的 capability_tags
  - 候选 Agent 列表（在线 + 有剩余负载）
  
输出：
  - 推荐排名：[{agent_id, score, matched_tags, missing_tags}]
```

### 5.2 匹配流程

```
Step 1: 过滤
  └─ Agent 状态 = online 且 load < max_concurrent_tasks
  
Step 2: 标签匹配（跨维度并集）
  └─ 需求标签 = 需求方所有维度标签的并集
  └─ Agent 标签 = Agent 所有维度标签的并集
  └─ 交集 = 需求标签 ∩ Agent 标签
  
Step 3: 打分
  └─ 匹配度 = Σ(交集中每个标签的 Agent 权重) / 需求标签总数
  └─ 如果权重未知（初始阶段），按 1.0 计算
  
Step 4: 排序
  └─ 优先：匹配度从高到低
  └─ 同分：负载从低到高（选最闲的）
  └─ 再同分：历史成功率从高到低
```

### 5.3 匹配度计算示例

```
Task 需要：
  {"python", "api_design", "coordination"}  (3 个标签)

Agent A 有：
  tags: {"python", "api_design", "fastapi", "coordination", "task_dispatch"}
  weights: {python: 0.6, api_design: 0.8, fastapi: 0.5, coordination: 0.9, task_dispatch: 0.7}

交集 = {"python", "api_design", "coordination"} (3 个全中)
得分 = (0.6 + 0.8 + 0.9) / 3 = 0.77

Agent B 有：
  tags: {"python", "coordination", "java"}
  weights: {python: 0.9, coordination: 0.5, java: 0.3}

交集 = {"python", "coordination"} (2/3)
得分 = (0.9 + 0.5) / 3 = 0.47

结果：Agent A (0.77) > Agent B (0.47)
```

### 5.4 不同层级的匹配策略

| 层级 | 需求标签来源 | 匹配宽松度 | 匹配数量 |
|------|-------------|-----------|---------|
| **Goal** | `capability_tags` (business + management) | 宽（有一个 business 标签即可） | 1 个（verifier） |
| **Project** | `capability_tags` (business + professional + management) | 中（需 50%+ 标签匹配） | 1 个（负责人） |
| **Task** | `capability_tags` (professional + technical + management) | 严（需 80%+ 标签匹配） | 1 个（执行者） |

---

## 6. 场景库设计

### 6.1 核心定义：场景 = 全集，目标 = 子集

**场景（Scenario）是一个全流程描述，类似于 PMBOK 之于项目管理。**

| 维度 | 场景（Scenario） | 目标（Goal） |
|------|-----------------|-------------|
| **类比** | PMBOK 全书 | 按 PMBOK 启动的一个实际项目 |
| **性质** | 方法论/框架 | 实际执行实例 |
| **内容** | 全流程描述 + 所有可能的分支 + 决策点 | 已经裁剪后的实际任务/工程 |
| **状态** | 静态的、可复用的知识资产 | 动态的、有生命周期的执行实例 |
| **变化** | 不变（除非有人编辑场景定义） | 执行中增删任务/工程，流程走向由现场决定 |
| **关系** | **全集** | **子集**（引用场景全集的一部分） |

### 6.2 场景的数据结构

场景存储的是一个"全集"——所有可能要做的事、所有可能的分支决策、所有可裁剪的建议。

**不使用 Phase 概念**，直接按 projects[] 列表组织，用 `next_step` 表达执行顺序，用 `condition` 表达分支决策。

```json
{
  "id": "chemical-leak-001",
  "name": "化工厂危化品泄漏应急预案",
  "level": "goal",
  "category": "emergency_response",
  "description": "化工厂发生危化品泄漏时的完整应急响应流程",
  
  "fullset": {
    "goal_tags": {
      "business": ["emergency_response", "chemical_hazard"],
      "professional": ["incident_command", "risk_assessment"],
      "technical": [],
      "management": ["coordination", "task_dispatch", "grasp_read", "grasp_write"]
    },
    
    "projects": [
      {
        "name": "应急响应",
        "type": "mandatory",
        "next_step": ["泄漏源控制"],
        "capability_tags": {
          "business": ["emergency_response"],
          "professional": ["incident_command"],
          "technical": ["python", "shell_scripting"],
          "management": ["coordination", "task_dispatch"]
        },
        "tasks": [
          {
            "name": "启动应急预案",
            "type": "mandatory",
            "next_step": ["通知指挥中心"],
            "capability_tags": {
              "business": ["emergency_response"],
              "professional": ["incident_command"],
              "technical": [],
              "management": ["coordination", "task_dispatch"]
            }
          },
          {
            "name": "通知指挥中心",
            "type": "mandatory",
            "capability_tags": {
              "business": ["emergency_response"],
              "professional": ["incident_command"],
              "technical": [],
              "management": ["coordination"]
            }
          }
        ]
      },
      {
        "name": "疏散",
        "type": "conditional",
        "condition": {
          "type": "human_decision",
          "prompt": "当前风向是什么？",
          "options": ["north", "south", "east", "west", "unknown"],
          "default": "unknown",
          "timeout_action": "use_default",
          "timeout_minutes": 30,
          "branches": {
            "north": { "next_projects": ["人员疏散南侧"], "next_tasks": ["evacuate_south"] },
            "south": { "next_projects": ["人员疏散北侧"], "next_tasks": ["evacuate_north"] },
            "unknown": { "next_projects": ["持续监测"], "next_tasks": ["monitor_wind"] }
          }
        },
        "capability_tags": {
          "business": ["evacuation_planning"],
          "professional": ["risk_assessment"],
          "technical": [],
          "management": ["coordination"]
        },
        "tasks": [
          {
            "name": "疏散南侧村庄",
            "type": "conditional",
            "condition": {
              "type": "auto_eval",
              "expr": "wind_direction == 'north'"
            },
            "capability_tags": {
              "business": ["evacuation_planning"],
              "professional": ["evacuation"],
              "technical": [],
              "management": ["coordination"]
            }
          }
        ]
      }
    ]
  }
}
```

### 6.3 场景与目标的关系

```
1. 创建 Goal："某化工厂泄漏了"
   → 系统匹配场景：化工厂危化品泄漏应急预案
   → Goal.scenario_id = "chemical-leak-001"

2. 初始裁剪（根据已知现场信息）：
   → 已知信息：有人报告泄漏，但风向未知、火情未知
   → 创建初始 Project + Task（只选 mandatory 和条件已满足的）：
     - Project: 应急响应
       - Task: 启动应急预案 ✅
       - Task: 通知指挥中心 ✅
     - Project: 泄漏源控制（跳过，因为泄漏源未确认）
     - Project: 疏散（跳过，因为风向未知）

3. 执行中动态调整：
   → 现场报告"风向是北风"
     → 引擎读取场景全集，条件 wind_direction == 'north' 满足
     → 创建 Project: 人员疏散南侧 + Task: 疏散南侧村庄
   
   → 现场报告"泄漏源已确认"
     → 引擎读取场景全集，条件 leak_source_confirmed 满足
     → 创建 Project: 泄漏源控制 + 对应任务
   
   → 现场报告"泄漏量很小，不需要大规模疏散"
     → 引擎根据场景中的可裁剪指南
     → 删除/跳过疏散 Project
```

**关键**：场景不是一次性实例化成完整的 Goal-Project-Task 树。它是在执行过程中**持续指导**Goal 的演进。

---

## 7. Human-in-the-Loop（HITL）设计

### 7.1 核心理念

**Task 是唯一的执行单元**。Goal 和 Project 提供组织能力，但不直接执行。HITL 的暂停和恢复最终都落到 Task 级别。

- **Goal 级 HITL** → 暂停/恢复该 Goal 下所有 Project 和 Task
- **Project 级 HITL** → 暂停/恢复该 Project 下所有 Task
- **Task 级 HITL** → 暂停/恢复该 Task 的执行

HITL 不是"问一个问题"，而是一个**完整的生命周期**：
```
场景定义（写蓝图） → 目标执行（暂停） → 人类响应 → 引擎恢复
```

### 7.2 三种 HITL 类型

| 类型 | 场景定义格式 | 目标执行时行为 | 适用场景 |
|------|-------------|---------------|---------|
| **信息收集** `human_input` | 填空式，需要人类提供具体信息 | 暂停，显示输入框，收集后存入 context → 继续执行 | "当前风向？"、"泄漏量多少？" |
| **决策选择** `human_decision` | 选择题，给选项 | 暂停，显示选项，人类选择 → 按 branches 走对应分支 | "是否疏散？A/B/C" |
| **争议仲裁** `human_arbitration` | 两个 Agent 方案冲突 | 暂停，展示两个方案对比，人类裁决 | "方案 A 用泡沫灭火 vs 方案 B 用水稀释" |

### 7.3 场景中的 HITL 定义

场景作者定义 HITL 条件：

```json
{
  "condition": {
    "type": "human_decision",
    "prompt": "根据当前火情，是否需要疏散周边人员？",
    "options": ["立即疏散", "暂缓，持续监测", "不需要"],
    "default": "暂缓，持续监测",
    "timeout_action": "use_default",
    "timeout_minutes": 30,
    "branches": {
      "立即疏散": { "next_projects": ["人员疏散"], "next_tasks": ["evacuate_all"] },
      "暂缓，持续监测": { "next_projects": ["持续监测"], "next_tasks": ["monitor"] },
      "不需要": null
    }
  }
}
```

字段说明：

| 字段 | 说明 | 必填 |
|------|------|------|
| `type` | HITL 类型：`human_input` / `human_decision` / `human_arbitration` | ✅ |
| `prompt` | 给人类的提示 | ✅ |
| `options` | 可选答案数组 | `human_decision` 必填 |
| `input_type` | 输入类型（text/number/select/multiline） | `human_input` 必填 |
| `default` | 超时默认值 | 推荐 |
| `timeout_action` | 超时行为：`use_default` / `skip_project` / `skip_task` / `escalate` | ✅ |
| `timeout_minutes` | 超时时间（分钟） | 推荐 |
| `branches` | 答案 → 分支映射 | `human_decision` 必填 |

### 7.4 目标执行时的 HITL 生命周期

```
Step 1: 引擎遇到 condition（非 auto_eval 类型）
  └─ 创建 HumanInputRequest 记录，status = pending
  └─ 暂停当前分支的所有 Task 调度
  └─ 状态：Goal/Project 标记为 awaiting_human_input

Step 2: 通知
  └─ 通知 Goal 的 verifier_agent（如刚子）
  └─ 通知场景定义的 responder_agents（如果有）
  └─ 前端显示"需要人类决策"弹窗
  └─ 推送通知到飞书/微信（可选）

Step 3: 人类响应
  └─ 人类点击弹窗，看到问题 + 选项/输入框
  └─ 人类选择/填写并提交
  └─ 更新 HumanInputRequest：status = answered, response = 答案
  └─ 记录 answered_at, responder_id

Step 4: 恢复执行
  └─ 引擎读取答案
  └─ 查 branches → 确定下一步
  └─ 创建对应的 Project/Task（或跳过）
  └─ 恢复 Goal 调度循环
  └─ 清除 awaiting_human_input 状态

Step 5: 超时处理
  └─ 超过 timeout_minutes 无人响应
  └─ 根据 timeout_action 执行：
     - use_default: 使用 default 值继续
     - skip_project: 跳过整个 Project
     - skip_task: 跳过当前 Task
     - escalate: 升级通知（通知更高级别的 verifier）
  └─ 记录超时事件
```

### 7.5 `human_input_requests` 表扩展

系统已有 `human_input_requests` 表，当前只关联 Task。需要扩展到支持 Goal 和 Project 级别。

**现有字段**：
```
id, task_id, title, description, input_type, status, 
input_data, submitted_by, submitted_at, context, 
created_at, updated_at
```

**新增字段**：
```
goal_id          TEXT    — Goal 级 HITL
project_id       TEXT    — Project 级 HITL
scenario_ref     TEXT    — 关联到场景的哪个 condition（如 "chemical-leak-001.projects[1].condition"）
default_value    TEXT    — 超时默认值
timeout_action   TEXT    — use_default / skip_project / skip_task / escalate
timeout_minutes  INTEGER — 超时时间
branches         TEXT    — JSON，答案到分支的映射
response         TEXT    — 人类的回答
responder_id     TEXT    — 回答者 ID
```

**字段互斥关系**：
- `task_id`、`project_id`、`goal_id` 三个字段**只能有一个非空**
- `task_id` 非空 → Task 级 HITL
- `project_id` 非空 → Project 级 HITL
- `goal_id` 非空 → Goal 级 HITL

### 7.6 执行引擎集成

调度器的 tick 循环需要增加 HITL 检查：

```python
async def _tick(self):
    # ... 现有逻辑 ...
    
    # HITL 检查：找出所有 pending 的 HumanInputRequest
    pending_requests = self._get_pending_human_requests()
    
    for req in pending_requests:
        # 检查是否超时
        if self._is_timed_out(req):
            await self._handle_timeout(req)
            continue
        
        # 暂停关联的 Goal/Project/Task 调度
        if req.goal_id:
            self._pause_goal(req.goal_id)
        elif req.project_id:
            self._pause_project(req.project_id)
        elif req.task_id:
            self._pause_task(req.task_id)
    
    # ... 继续正常调度 ...
```

### 7.7 前端 UI

根据 `input_type` 渲染不同界面：

| input_type | UI 组件 |
|-----------|---------|
| `human_input` (text) | 文本输入框 + 提交按钮 |
| `human_input` (number) | 数字输入框 |
| `human_input` (multiline) | 多行文本框 |
| `human_decision` | 单选按钮组 / 下拉选择 |
| `human_arbitration` | 左右对比面板（方案 A vs 方案 B）+ 选择按钮 |

---

## 8. 数据库变更

### 8.1 ALTER TABLE

```sql
-- Agent 表：重命名 capabilities 为 capability_tags
ALTER TABLE agents RENAME COLUMN capabilities TO capability_tags;

-- Goal 表：新增 capability_tags
ALTER TABLE goals ADD COLUMN capability_tags TEXT DEFAULT '{}';

-- Project 表：新增 capability_tags
ALTER TABLE projects ADD COLUMN capability_tags TEXT DEFAULT '{}';

-- Task 表：替换 category 为 capability_tags
ALTER TABLE tasks ADD COLUMN capability_tags TEXT DEFAULT '{}';
ALTER TABLE tasks DROP COLUMN category;

-- Scenario 表：新增 fullset 字段
ALTER TABLE scenarios ADD COLUMN fullset TEXT DEFAULT '{}';

-- human_input_requests 表：扩展支持 Goal/Project 级 HITL
ALTER TABLE human_input_requests ADD COLUMN goal_id TEXT;
ALTER TABLE human_input_requests ADD COLUMN project_id TEXT;
ALTER TABLE human_input_requests ADD COLUMN scenario_ref TEXT;
ALTER TABLE human_input_requests ADD COLUMN default_value TEXT;
ALTER TABLE human_input_requests ADD COLUMN timeout_action TEXT;
ALTER TABLE human_input_requests ADD COLUMN timeout_minutes INTEGER;
ALTER TABLE human_input_requests ADD COLUMN branches TEXT;
ALTER TABLE human_input_requests ADD COLUMN response TEXT;
ALTER TABLE human_input_requests ADD COLUMN responder_id TEXT;
```

### 8.2 数据迁移

```sql
-- Agent 数据迁移：capabilities array → capability_tags object
UPDATE agents SET capability_tags = (
  SELECT json_object(
    'business', json_array(),
    'professional', json_array(),
    'technical', capabilities,
    'management', json_array()
  )
  FROM agents a WHERE a.id = agents.id
);
```

### 8.3 权重存储

权重单独一个表：

```sql
CREATE TABLE agent_tag_weights (
    agent_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    last_observed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (agent_id, tag)
);
```

---

## 9. 实施计划

### Phase 1: DB + ORM 模型
- [ ] SQL 迁移脚本（ALTER + 数据迁移）
- [ ] Task/Project/Goal/Agent ORM 模型更新
- [ ] Agent 权重表创建

### Phase 2: 匹配引擎
- [ ] 重写 agent_matcher.py，支持多维度匹配
- [ ] 权重计算逻辑
- [ ] 自动标注信号采集点

### Phase 3: API 路由
- [ ] Goal/Project/Task 的 capability_tags CRUD
- [ ] 场景 fullset 字段
- [ ] 匹配端点（POST /match）

### Phase 4: HITL
- [ ] human_input_requests 表扩展
- [ ] 调度器 HITL 检查集成
- [ ] 前端 HITL 弹窗 UI
- [ ] 超时处理逻辑

### Phase 5: 前端
- [ ] api.ts 类型定义更新
- [ ] AgentList 页面：标签编辑
- [ ] TaskList/ProjectList/GoalDetail 页面：标签展示和编辑
- [ ] ScenarioCenter 页面：场景全集配置

### Phase 6: 测试
- [ ] 匹配逻辑单元测试
- [ ] API 端点回归测试
- [ ] HITL 端到端测试
- [ ] 页面渲染验证（四板斧）

---

## 10. 关键决策记录

| 决策 | 内容 | 原因 |
|------|------|------|
| 字段名 | 统一用 `capability_tags` | 零映射，零别名，匹配引擎只认一个字段 |
| 数据结构 | JSON object（四维）而非 array | 支持维度分类和跨维度匹配 |
| 权重存储 | 单独表 `agent_tag_weights` | 避免 tags 和 weights 混在一起，查询更灵活 |
| 旧字段处理 | Agent 的 `capabilities` 直接改名为 `capability_tags` | 不保留映射，干净利落 |
| Task 的 `category` | 直接删除，用 `capability_tags` 替代 | 不需要过渡期，一步到位 |
| 场景定位 | 场景 = 全集，Goal = 子集 | 场景是方法论框架（类似 PMBOK），Goal 是实际执行时从全集中裁剪出的子集 |
| 实例化方式 | 不一次性实例化，执行中动态增减 | 根据运行时现场信息从场景全集中按需选取任务/工程 |
| 流程控制 | 使用 `next_step` 而非 Phase | 系统已有 next_step 字段，不需要引入新概念 |
| HITL 定位 | Task 是唯一执行单元 | Goal/Project 暂停/恢复最终都落到 Task 级别 |
| 自动标注 | 系统能力标签自动推断 | 管理能力不手动配，通过运行时行为自动标注 |
