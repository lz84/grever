# Nexus HITL（Human-in-the-Loop）设计文档

**日期**: 2026-05-23
**性质**: 产品设计 + 实现方案
**参与**: 用户 + 刚子

---

## 一、为什么 HITL 是产品分水岭

### 真实世界里没有全自动的高价值工作

| 场景 | 没有 HITL | 有 HITL |
|------|----------|---------|
| 软件开发 | AI 直接用了 Redis，但客户已经有 Memcached 运维工具 → 全白干 | AI 提方案，人拍板用 Memcached，AI 干活 |
| 化工应急 | AI 建议疏散半径 500 米，但下风向有学校 → 出人命 | AI 计算，人改成 1000 米，AI 重新执行 |
| 代码审查 | AI 判断"这段代码风格不对"但标准可能是错的 | 人定标准，AI 逐行检查，人最终确认 |

**HITL 不是拖慢效率，是让 AI 不会走偏。**

### 差异化优势

| 竞品 | HITL 能力 |
|------|----------|
| AutoGen/CrewAI | 没有 |
| LangChain | 手动加 Human-in-the-Loop 节点，很麻烦 |
| Palantir | 有，但只在顶层，粒度粗 |
| **Nexus** | **每个 Task 都可以设 HITL，细粒度控制** |

**核心差异化一句话**：

> 别人要么全自动（走偏了不管），要么全手动（效率低）。我们是"AI 干活，人把关"。

---

## 二、HITL 的三种场景

### 场景一：创建场景时定义 HITL

在场景蓝图编辑中，为每个 Task 设置一个字段：**执行模式（executor_type）**。

#### 执行模式（executor_type）

| 值 | 含义 | 示例 |
|----|------|------|
| `ai` | AI 直接干 | 水位监测、预警发布 |
| `ai_approval` | AI 干，先等人批 | AI 算疏散方案，人批了再执行 |
| `ai_data` | AI 干，中途要人给数据 | AI 算疏散范围，要人输入当前风力 |
| `ai_confirm` | AI 干完，人验 | AI 修复 Bug，人验证对不对 |
| `human` | 纯人干 | 现场人员清点、电话通知上级 |
| `auto_eval` | 自动评估 | 自动判断是否满足条件后执行 |

#### 场景编辑页面设计

```
┌────────────────────────────────────────────────────────────┐
│ 场景：危化品泄漏应急处置                                       │
├────────────────────────────────────────────────────────────┤
│ Phase 1: 应急响应                                             │
│                                                              │
│  ☐ 水位监测        [AI ▼]           AI 直接干                 │
│  ☐ 预警发布        [AI ▼]           AI 直接干                 │
│  ☐ 启动应急响应    [审批 ▼]         ⚡ AI 干，先等人批          │
│  ☐ 疏散范围计算    [数据 ▼]         ⚡ AI 干，中途要数据         │
│                                                              │
│ Phase 2: 现场处置                                             │
│                                                              │
│  ☐ 泄漏源封堵      [审批 ▼]         ⚡ AI 干，先等人批          │
│  ☐ 人员清点        [纯人 ▼]         现场人员手工完成            │
│  ☐ 环境监测        [确认 ▼]         ⚡ AI 干完，人验            │
│                                                              │
│ [AI = AI直接干]  [审批 = 先等人批]  [数据 = 中途要数据]          │
│ [确认 = 干完人验]  [纯人 = 人干活]  [自动 = 自动评估]            │
└────────────────────────────────────────────────────────────┘
```

#### HITL 配置弹窗

选中 `ai_approval` / `ai_data` / `ai_confirm` 时弹出：

```
┌──────────────────────────────────────────┐
│ 配置 HITL 节点                            │
├──────────────────────────────────────────┤
│                                          │
│ HITL 标题：是否启动 I 级应急响应？           │
│ HITL 说明：根据泄漏等级和影响范围，          │
│ 决定是否启动最高级别应急响应。               │
│                                          │
│ 超时设置：[30 ▼] 分钟                      │
│                                          │
│ 超时动作：                                 │
│   ● 使用默认值（不启动）                    │
│   ○ 自动升级（通知更高级别领导）             │
│   ○ 暂停等待                               │
│                                          │
│ 默认值：[不启动 ▼]                         │
│                                          │
│ 审批人：                                   │
│   ○ 任意登录用户                           │
│   ○ 指定角色：[安全负责人 ▼]                │
│   ○ 指定人员：[__________]                 │
│                                          │
│          [取消]        [确定]              │
└──────────────────────────────────────────┘
```

---

### 场景二：脱离场景时，直接创建任务定义 HITL

在 Goal / Project / Task 创建页面中增加执行模式下拉框。

#### CreateTask 页面

```
┌────────────────────────────────────────────────┐
│ 创建任务                                        │
│                                                │
│ 任务标题：[                        ]            │
│ 描述：    [                        ]            │
│ 优先级：  [ 中 ] ▼                               │
│ 分配给：  [      ▼]                              │
│                                                │
│ 执行模式：                                      │
│   ● AI 直接干                                   │
│   ○ AI 干，先等人批                              │
│   ○ AI 干，中途要人给数据                        │
│   ○ AI 干完，人验                               │
│   ○ 纯人干                                     │
│   ○ 自动评估                                   │
│                                                │
│ [选中审批/数据/确认后展开 HITL 配置]             │
│                                                │
│ 审批标题：[                        ]            │
│ 说明：    [                        ]            │
│                                                │
│ 超时：  [    ] 分钟   默认值：[        ]        │
│ 审批人：[任意用户 ▼]                             │
│                                                │
└────────────────────────────────────────────────┘
```

#### TaskDetail 页面随时加 HITL

任务跑着跑着，发现"这个我得看看"，可以直接在 TaskDetail 里加一个"加审批"按钮。

**状态安全校验**：

| Task 状态 | 能否加 HITL | 说明 |
|----------|------------|------|
| `todo` | ✅ | 直接设为 waiting_human + 创建请求 |
| `in_progress` | ✅ | 暂停执行 → 设为 waiting_human + 创建请求 |
| `paused` | ✅ | 直接设为 waiting_human + 创建请求 |
| `done` | ❌ | 已完成，不能加 |
| `failed` | ❌ | 已失败，应该重试而不是加 HITL |
| `waiting_human` | ❌ | 已经在等了，重复创建无意义 |
| `blocked` | ❌ | 还没轮到这个任务，不需要加 |

---

### 场景三：运行时随时干预

不只是预设的 HITL，还要有**随时打断**的能力。

#### 任务执行中的控制按钮

```
任务：泄漏源封堵 正在执行中...
─────────────────────────────────────
⏸ 暂停    🛑 终止    👤 人工接管
```

| 操作 | 状态变更 | 场景 |
|------|---------|------|
| **暂停** | `in_progress` → `paused` | "等一下，我先看看现场情况" |
| **终止** | `in_progress` → `failed` | "这个方案不对，换一个" |
| **人工接管** | `in_progress` → `human_taking_over` | "这个太复杂了，我来" |

---

## 三、HITL 完整流程

```
                    ┌──────────────────┐
                    │    定义阶段        │
                    │  (创建/编辑)       │
                    └────────┬─────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
      ┌─────┴──────┐  ┌─────┴─────┐   ┌──────┴──────┐
      │ 场景蓝图创建 │  │ 直接创建   │   │ 运行时随时  │
      │ executor_   │  │ Task 页面  │   │ 加/改/删   │
      │ type 字段   │  │ 选执行模式  │   │ HITL 配置  │
      └─────┬───────┘  └─────┬──────┘   └──────┬──────┘
            │                │                 │
            └────────────────┼─────────────────┘
                             │
                    ┌────────┴─────────┐
                    │    实例化阶段      │
                    │  (事务包裹)        │
                    └────────┬─────────┘
                             │
                    ┌────────┴─────────┐
                    │ executor_type    │
                    │ 写入 Task 记录    │
                    └────────┬─────────┘
                             │
                    ┌────────┴─────────┐
                    │    执行阶段        │
                    └────────┬─────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
      ┌─────┴──────┐  ┌─────┴─────┐   ┌──────┴──────┐
      │ 纯人        │  │ AI + 审批  │   │ AI 直接     │
      │ waiting    │  │ waiting   │   │ todo        │
      │ _human     │  │ _human    │   │             │
      │ (直接审批)  │  │ → AI 执行  │   │             │
      └─────┬──────┘  └─────┬──────┘   └──────────────┘
            │               │
            │         ┌─────┴─────┐
            │         │ 审批通过   │  审批拒绝
            │         │ → todo    │  → failed
            │         │ → AI 执行 │  → 下游阻塞
            │         └─────┬─────┘
            │               │
            └───────┬───────┘
                    │
            ┌───────┴────────────────┐
            │  人审批/输入            │
            │                        │
            │  通过 → done/AI 执行   │
            │  拒绝 → failed         │
            │  超时 → 按策略          │
            │                        │
            │  unlock 下游           │
            │  依赖任务              │
            └────────────────────────┘
```

---

## 四、现有基础盘点（已有 70%）

### 4.1 数据库层

**`human_input_requests` 表**（Migration 016）：

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | VARCHAR(36) | 主键 |
| `task_id` | VARCHAR(36) | 关联任务 |
| `title` | VARCHAR(255) | 标题 |
| `description` | VARCHAR(2000) | 说明 |
| `input_type` | VARCHAR(50) | 类型（approval/confirmation/data） |
| `status` | VARCHAR(20) | pending/submitted/rejected/expired |
| `input_data` | JSON | 人类提交的数据 |
| `submitted_by` | VARCHAR(100) | 提交人 |
| `submitted_at` | DATETIME | 提交时间 |
| `context` | JSON | 上下文信息 |
| `goal_id` | TEXT | 目标关联 |
| `project_id` | TEXT | 项目关联 |
| `scenario_ref` | TEXT | 场景引用 |
| `default_value` | TEXT | 默认值 |
| `timeout_action` | TEXT | 超时动作 |
| `timeout_minutes` | INTEGER | 超时分钟数 |
| `branches` | TEXT | 分支（审批后的不同走向） |
| `response` | TEXT | 响应 |
| `responder_id` | TEXT | 响应人 |

**需要新增的字段**（审计 + 权限 + 执行模式）：

| 新增列 | 类型 | 说明 |
|--------|------|------|
| `required_role` | TEXT | 需要什么角色才能审批 |
| `assigned_to` | TEXT | 指定谁能审批 |
| `approval_reason` | TEXT | 审批理由（MVP 必填） |
| `before_snapshot` | JSON | 审批前的状态快照 |
| `executor_type` | VARCHAR(20) | 执行模式，默认 `ai` |

**`executor_type` 字段位置**：

| 表 | 说明 |
|----|------|
| `scenario_tasks` | ✅ 场景蓝图定义执行模式 |
| `tasks` | ✅ 实例化时带入，标识这个任务怎么执行 |

### 4.2 后端 API

| API | 方法 | 状态 |
|-----|------|------|
| `GET /api/v1/human-input/pending` | 查询待处理请求 | ✅ |
| `GET /api/v1/human-input/{input_id}` | 获取详情 | ✅ |
| `POST /api/v1/human-input/{input_id}/submit` | 提交输入 | ✅ |
| `POST /api/v1/human-input/{input_id}/reject` | 拒绝 | ✅ |
| `GET /api/v1/human-input/task/{task_id}` | 查询任务相关请求 | ✅ |
| `GET /api/v1/human-input/recent` | 最近请求 | ✅ |
| `GET /api/v1/human-input/stats` | 统计数据 | ✅ |
| `GET /api/v1/human-input/review-stats` | 人类审核统计 | ✅ |

### 4.3 执行链路

| 组件 | 状态 | 说明 |
|------|------|------|
| `waiting_human` Task 状态 | ✅ | 状态机已支持 |
| `_handle_human_input` | ✅ | `tasks_execution_core.py` 检测 AI 返回的 needs_human_input |
| `DependencyResolver.unlock_on_human_input` | ✅ | 人类提交后自动解锁下游依赖任务 |
| `DependencyResolver.scan_blocked_tasks` | ✅ | 自动检测依赖阻塞的任务 |
| 飞书通知 | ✅ | `feishu_notification.py`，waiting_human 时推送 |
| 超时处理 | ✅ | `timeout_handler.py`，waiting_human 超时自动处理 |
| `scenario_instantiate_v2.py` 实例化逻辑 | ⚠️ | 需要按 executor_type 重写 |

### 4.4 前端

| 页面 | 状态 | 说明 |
|------|------|------|
| HumanInputPage | ✅ | 待处理列表 + 详情 + 提交 |
| HumanInputDashboard | ✅ | 统计仪表盘 |
| HumanInputAnalytics | ✅ | 分析页面 |
| TaskStatus 状态徽章 | ✅ | waiting_human 显示紫色 |

---

## 五、缺失的关键桥梁

### 缺失 1：实例化时不创建 HITL 请求

**现状**：`scenario_instantiate_v2.py` 对需要 HITL 的任务直接跳过，不创建 Task。

**修复方案**：按 `executor_type` 组合逻辑创建 Task + human_input_request。

### 缺失 2：执行前不拦截

**现状**：Agent 领到任务直接干，不检查 Task 是否是 `waiting_human`。

**修复方案**：在 `task_runner.py` / `project_executor.py` 领任务时检查，`waiting_human` 跳过执行。

### 缺失 3：前端没有场景 HITL 视图

**现状**：HumanInputPage 是通用页面，没有和场景实例化关联。

**修复方案**：ScenarioDetail 页加"HITL 审批"Tab。

---

## 六、实现方案：分三步走

### 第一步：实例化创建 HITL（半天）

**目标**：按 `executor_type` 正确创建 Task + human_input_request。

**修改文件**：`scenario_instantiate_v2.py`

**逻辑**：

```
遍历场景 Tasks
  → executor_type = ai:
     → 创建 Task（status = todo，executor_type = ai）

  → executor_type = auto_eval:
     → 创建 Task（status = todo，executor_type = auto_eval）

  → executor_type = human:
     → 创建 Task（status = waiting_human，executor_type = human）
     → 创建 human_input_request（纯审批，无 AI 执行环节）

  → executor_type = ai_approval:
     → 创建 Task（status = waiting_human，executor_type = ai_approval）
     → 创建 human_input_request（审批通过后 AI 开始执行）

  → executor_type = ai_data:
     → 创建 Task（status = waiting_human，executor_type = ai_data）
     → 创建 human_input_request（给完数据后 AI 开始执行）

  → executor_type = ai_confirm:
     → 创建 Task（status = todo，executor_type = ai_confirm）
     → 注意：confirm 是后置，实例化时直接 todo，AI 先干
```

**核心代码**：

```python
def _create_task_with_executor(conn, task_data, goal_id, project_id, now):
    """在事务中创建 Task + HITL 请求"""
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    executor_type = task_data.get('executor_type', 'ai')

    # 决定 Task 状态
    if executor_type in ('human', 'ai_approval', 'ai_data'):
        task_status = 'waiting_human'
        needs_hitl = True
    elif executor_type == 'ai_confirm':
        task_status = 'todo'
        needs_hitl = False  # confirm 是后置，AI 先干
    else:
        task_status = 'todo'
        needs_hitl = False

    # 创建 Task
    conn.execute(text("""
        INSERT INTO tasks (id, title, description, project_id, goal_id, status, executor_type, ...)
        VALUES (:id, :title, :desc, :project_id, :goal_id, :status, :executor_type, ...)
    """), {
        "id": task_id,
        "title": task_data['name'],
        "desc": task_data['description'] or "",
        "project_id": project_id,
        "goal_id": goal_id,
        "status": task_status,
        "executor_type": executor_type,
    })

    # 如果需要 HITL，在同一事务中创建请求
    if needs_hitl:
        condition_data = json.loads(task_data.get('condition_data', '{}')) if task_data.get('condition_data') else {}

        input_type_map = {
            'ai_approval': 'approval',
            'ai_data': 'data',
            'ai_confirm': 'confirmation',
        }
        input_type = input_type_map.get(executor_type, 'approval')

        # 幂等保护：检查是否已存在
        existing = conn.execute(text("""
            SELECT id FROM human_input_requests
            WHERE task_id = :task_id AND status = 'pending'
        """), {"task_id": task_id}).fetchone()
        if existing:
            return task_id

        hitl_id = f"hitl-{uuid.uuid4().hex[:12]}"
        conn.execute(text("""
            INSERT INTO human_input_requests
            (id, task_id, goal_id, project_id, title, description,
             input_type, status, default_value, timeout_action, timeout_minutes,
             required_role, assigned_to, created_at, updated_at)
            VALUES
            (:id, :task_id, :goal_id, :project_id, :title, :desc,
             :input_type, 'pending', :default_value, :timeout_action, :timeout_minutes,
             :required_role, :assigned_to, :now, :now)
        """), {
            "id": hitl_id,
            "task_id": task_id,
            "goal_id": goal_id,
            "project_id": project_id,
            "title": condition_data.get('hitl_title', task_data['name']),
            "desc": condition_data.get('hitl_description', ''),
            "input_type": input_type,
            "default_value": condition_data.get('default_value'),
            "timeout_action": condition_data.get('timeout_action', 'use_default'),
            "timeout_minutes": condition_data.get('timeout_minutes', 30),
            "required_role": condition_data.get('required_role'),
            "assigned_to": condition_data.get('assigned_to'),
            "now": now,
        })

    return task_id
```

### 第二步：执行前拦截（半天）

**目标**：Agent 领到 `waiting_human` 任务时跳过执行，等人类审批。

**修改文件**：`task_runner.py` 或 `project_executor.py`

**逻辑**：

```
领任务 → 检查 status
  → waiting_human → 跳过执行，log 记录，保持 waiting_human 状态
  → 其他 → 正常执行
```

**注意**：下游任务的依赖阻塞由 `DependencyResolver` 自动处理。

### 第三步：前端打通（1 天）

**目标**：ScenarioDetail 页加"HITL 审批"Tab + TaskDetail 可随时加 HITL + CreateTask 加执行模式选择。

**3.1 ScenarioDetail 加 HITL Tab**

**3.2 TaskDetail 加"加审批"按钮**

**3.3 CreateTask 加执行模式下拉框**

---

## 七、审批结果处理与依赖解锁

### 7.1 审批结果状态流转

| 审批结果 | Task 状态 | 下游处理 |
|---------|----------|---------|
| **通过**（approve） | `executor_type = human` → `done`<br>`executor_type = ai_approval/ai_data` → `todo`（AI 开始干） | `unlock_on_human_input` → 下游解锁 |
| **拒绝**（reject） | `failed` | 下游继续阻塞 |
| **超时 → 使用默认值** | 按 default_value 决定 | 同通过或同拒绝 |
| **超时 → 自动升级** | 保持 `waiting_human` | 通知上级，继续等待 |
| **超时 → 暂停等待** | 保持 `waiting_human` | 不处理 |

### 7.2 审批通过流程

```
人类提交审批（通过）
  → POST /api/v1/human-input/{input_id}/submit
  → 更新 human_input_requests：status = 'submitted'
  → 查询 Task 的 executor_type：
    → human → Task status = 'done'
    → ai_approval / ai_data → Task status = 'todo'（AI 开始执行）
  → 调用 DependencyResolver.unlock_on_human_input(input_id)
  → 下游任务解锁为 todo
  → 飞书通知
```

### 7.3 审批拒绝流程

```
人类提交审批（拒绝）
  → Task status = 'failed'
  → 下游继续阻塞
  → 飞书通知
```

> MVP 阶段先不做 branches。

### 7.4 超时处理

```
timeout_handler 定时扫描
  → 查询 status = 'waiting_human' 的任务
  → 超时后按 timeout_action 处理
  → 更新状态 + 通知
```

---

## 八、权限控制

| HITL 级别 | 审批人要求 | 实现方式 |
|----------|-----------|---------|
| 普通审批 | 任意登录用户 | `required_role = NULL` |
| 角色审批 | 指定角色 | `required_role = 'safety_officer'` |
| 指定人审批 | 指定具体人员 | `assigned_to = 'ou_zhangsan'` |

前端：不符合权限的用户，审批按钮灰色 + 提示"您没有审批此任务的权限"。

---

## 九、审计与追溯

### 审计字段

| 字段 | 存储位置 | 状态 |
|------|---------|------|
| 谁审批的 | `human_input_requests.submitted_by` | ✅ 已有 |
| 什么时候审批的 | `human_input_requests.submitted_at` | ✅ 已有 |
| 审批理由 | `human_input_requests.approval_reason` | ❌ 需新增（MVP 必填） |
| 拒绝理由 | `human_input_requests.rejected_reason` | ✅ 已有 |
| 审批前状态快照 | `human_input_requests.before_snapshot` | ❌ 需新增 |

**最小审计要求**（MVP 必须）：
- 审批理由必填
- 所有审批记录不可删除、不可修改

---

## 十、运行时控制（后续迭代）

### 紧急中断

| 操作 | 状态变更 |
|------|---------|
| 暂停 | `in_progress` → `paused` |
| 终止 | `in_progress` → `failed` |
| 人工接管 | `in_progress` → `human_taking_over` |

### 后置确认

> `ai_confirm` 模式：AI 干完 → `pending_confirm` → 人确认 → done
> 不在 MVP 范围内，后续迭代。

---

## 十一、HITL 的商业价值

### 对化工应急客户

> "你的预案里每一步谁拍板、需要什么信息，都可以预设好。系统自动执行，到关键节点自动等你审批。不是替代人，是让 AI 帮你把预案跑起来。"

### 对软件开发客户

> "AI 帮你写代码、做审查，但架构选型、代码风格标准，你来定。AI 干活，你把关。"

### 核心卖点

| 卖点 | 说明 |
|------|------|
| **AI 干活，人把关** | 不是替代人，是让人从执行者变成决策者 |
| **细粒度控制** | 每个任务都能设置 HITL |
| **随时介入** | 随时能暂停、终止、接管 |
| **全程可追溯** | 所有人工决策有记录 |
| **权限可控** | 不同级别审批对应不同角色 |

---

## 十二、验收标准

### 第一步验收（实例化创建）

- [ ] `executor_type = ai` → Task 状态为 `todo`
- [ ] `executor_type = human` → Task 状态为 `waiting_human` + 创建 human_input_request
- [ ] `executor_type = ai_approval` → Task 状态为 `waiting_human` + 创建 human_input_request
- [ ] `executor_type = ai_data` → Task 状态为 `waiting_human` + 创建 human_input_request
- [ ] `executor_type = ai_confirm` → Task 状态为 `todo`（AI 先干）
- [ ] **事务一致性**：Task 和 request 要么都创建，要么都不创建
- [ ] **幂等保护**：重复实例化不重复创建 human_input_request
- [ ] 飞书通知能收到

### 第二步验收（执行前拦截）

- [ ] Agent 领到 `waiting_human` 任务时跳过执行
- [ ] 下游依赖任务被正确阻塞
- [ ] **human 审批通过** → Task done → 解锁下游
- [ ] **ai_approval 审批通过** → Task todo → AI 开始执行
- [ ] **审批拒绝** → Task failed → 下游阻塞

### 第三步验收（前端打通）

- [ ] 场景编辑页面能选择 executor_type（AI/审批/数据/确认/纯人）
- [ ] CreateTask 能选择 executor_type
- [ ] ScenarioDetail 的 HITL Tab 显示等待人类的节点
- [ ] 状态安全校验：done/failed/waiting_human 不可加 HITL

---

*本文档由用户 + 刚子于 2026-05-23 讨论形成，是 Nexus HITL 功能的完整设计文档。*
