# Nexus 智能体协同驾驭平台 - 御（Reins）架构设计

**版本**: v1.7  
**作者**: 麻子  
**最后更新**: 2026-04-09 11:54  

---

## 1. 概述

**Reins（御）** 是 Nexus 平台的 Agent 协作框架，采用**服务端精简 + Agent 自治**的设计原则。

### 1.1 核心职责划分

**服务端（Nexus Server）职责**:
- 目标管理
- 项目管理
- 任务管理
- Agent 发现与注册
- 争议处理

**Agent 端（自治）职责**:
- 协作流程
- 本地技能/认知
- 工作流执行
- 跨 Agent 协调

**Reins 本质**：
Reins 是**协作流程抽象**（下沉到 Agent 端）与**Paperclip 状态机基础设施**的融合。协作技能属于 Agent 端技能，不是服务端的职责。服务端只提供基础任务分发，协作细节由 Agent 自行决定。

### 1.2 设计原则：Human on the Loop

**核心理念**：**最小化人类介入，最大化 Agent 自主**

人类只在**关键节点**介入，其他全部由 Agent 自主完成。

**人类介入节点**:

| 介入节点 | 人类职责 | Agent 职责 | 示例 |
|---------|---------|-----------|------|
| **目标设定** | 输入高层目标和约束 | 目标分解为可执行任务 | 用户输入"创建 Nexus 项目"，Agent 分解为初始化、配置、测试等子任务 |
| **重大决策** | 审批关键路径决策 | 提供决策建议和风险评估 | Agent 提议"切换到新架构"，人类审批后执行 |
| **异常处理** | 处理无法自愈的异常 | 尝试自动修复、回滚、降级 | Agent 重试 3 次失败后，请求人类介入排查 |

**Agent 自主执行范围**:

- ✅ **任务分解与规划** - LLM 驱动的任务自动分解
- ✅ **Agent 协作与协调** - 通过协作技能自行协商任务分配
- ✅ **技能调用与执行** - 调用 Reach 等 Agent 的技能
- ✅ **状态同步与反馈** - 实时状态更新
- ✅ **异常自愈与重试** - 自动重试、回滚、降级策略

**与传统工作流引擎对比**:

| 维度 | 传统工作流引擎 | Nexus Reins (Human on the Loop) |
|------|---------------|--------------------------------|
| 人类介入 | 频繁（需要配置每个步骤） | 最小化（只在关键节点） |
| Agent 自主 | 无（严格按预设流程） | 全自主（在目标框架内自由决策） |
| 灵活性 | 低（难以应对变化） | 高（Agent 自适应调整） |
| 适用场景 | 固定流程、确定性任务 | 复杂场景、需要智能决策的任务 |

**与"Human in the Loop"的区别**:

| 模式 | 人类角色 | 适用场景 |
|------|---------|---------|
| **Human in the Loop** | 每个步骤都需要人类确认 | 高风险、完全确定的流程 |
| **Human on the Loop** | 只在关键节点介入 | 复杂、需要 Agent 自主决策的场景 |

**Reins 的设计哲学**:
- **信任 Agent** - 在明确的目标框架内，Agent 可以自主决策
- **人类把关** - 人类负责设定目标和审批重大决策
- **自动化优先** - 能自动解决的，绝不打扰人类

### 1.3 简化前后对比

| 维度 | v1.3（复杂） | v1.4（简化） | v1.5（职责完善） |
|------|-------------|-------------|------------------|
| 服务端职责 | 目标分解、任务分配、协作编排、状态同步 | 目标/项目/任务管理、Agent 注册、争议处理 | **6 大完整职责**：目标、项目、任务、Agent 注册/发现、争议管理 |
| 协作流程 | 服务端工作流引擎编排 | Agent 端通过协作技能自行协调 | 保持 Agent 自治，增强服务端注册发现能力 |
| 状态机 | 服务端维护复杂状态机 | Paperclip Issue 状态机（todo→in_progress→done） | 保持 Paperclip Issue 状态机 |
| Agent 通信 | 通过 Reins 协调 | A2A Hub 直连，Agent 自主决策 | 发现后 A2A 直连，不经 Reins 中转 |
| 复杂度 | 高（服务端承担太多） | 低（职责清晰，各司其职） | 清晰（6 大职责明确） |

**Paperclip 现状（Reins 的基础）**:
- Paperclip = Issue 管理（状态机：todo→in_progress→done）
- Paperclip = Agent 触发（heartbeat run）
- Paperclip = 任务执行层

**Reins 基于 Paperclip**:

```
Reins = Paperclip（骨骼）+ 协作技能（Agent 自治）

Reins 基于 Paperclip：
├── Paperclip 提供状态机、Issue 管理、任务触发
├── Agent 端协作技能提供：
│   ├── 任务协商（哪个 Agent 做什么）
│   ├── 流程编排（任务执行顺序）
│   ├── 异常处理（错误时如何协调）
│   └── 上下文共享（Agent 间如何传递信息）
└── 服务端只提供任务分发，不干涉协作细节
```

**核心能力**:
- **服务端**：任务分发、Agent 注册、争议仲裁
- **Agent 端**：协作流程执行、技能调用、跨 Agent 协调
- **协作技能**：每个 Agent 拥有自己的协作技能包（作为本地认知）

### 1.5 Reins 服务端完整职责

**Reins 服务端职责清单**（6 大职责）:

| 职责 | 说明 | 主要功能 |
|------|------|---------|
| **目标管理** | 目标的创建、分解、跟踪 | 接收高层目标，分解为可执行任务，跟踪执行进度 |
| **项目管理** | 项目的创建、成员、进度 | 创建项目、管理项目成员、跟踪项目整体进度 |
| **任务管理** | 任务的分配、状态、流转 | 任务分配、状态追踪、任务流转控制 |
| **Agent 注册** | Agent 的注册、注销、心跳 | Agent 注册/注销、心跳保持、状态更新 |
| **Agent 发现** | 按能力/状态查询 Agent | 能力查询、状态查询、Agent 列表返回 |
| **争议管理** | Agent 间冲突的裁决和处理 | 冲突检测、裁决决策、仲裁执行 |

#### 1.5.1 目标管理

**职责描述**:
服务端提供目标的全生命周期管理能力，包括目标创建、目标分解、目标跟踪。

**核心功能**:
- **目标创建**：接收高层目标描述，创建目标记录
- **目标分解**：利用 LLM 能力将高层目标分解为可执行的任务序列
- **目标跟踪**：跟踪目标的执行进度，提供进度可视化
- **目标调整**：支持目标在执行过程中的动态调整

**目标数据结构**:
```yaml
目标 ID：goal-001
名称：Nexus 项目初始化
描述：完成 Nexus 平台的初始化配置
分解任务：
  - task-001：项目结构创建
  - task-002：依赖配置
  - task-003：环境初始化
  - task-004：测试验证
状态：in_progress
进度：75%
创建时间：2026-04-02T10:00:00Z
```

#### 1.5.2 项目管理

**职责描述**:
服务端提供项目的创建、成员管理、进度跟踪能力。

**核心功能**:
- **项目创建**：创建项目，配置项目参数
- **成员管理**：添加/移除项目成员，分配角色
- **进度跟踪**：汇总所有任务进度，提供项目整体进度
- **资源管理**：管理项目相关的计算资源、存储空间

**项目数据结构**:
```yaml
项目 ID：proj-001
名称：Nexus 平台开发
目标关联：goal-001
成员：
  - agent：reach (role: developer)
  - agent：vigil (role: security)
  - agent：grasp (role: analyst)
任务列表：
  - task-001
  - task-002
  - task-003
  - task-004
状态：active
创建时间：2026-04-02T10:00:00Z
```

#### 1.5.3 任务管理

**职责描述**:
服务端提供任务的创建、分配、状态追踪、流转控制能力。

**核心功能**:
- **任务创建**：根据目标分解创建任务
- **任务分配**：将任务分配给合适的 Agent
- **状态追踪**：实时追踪任务执行状态
- **流转控制**：控制任务状态流转（todo→in_progress→done）
- **依赖管理**：管理任务间的依赖关系

**任务数据结构**:
```yaml
任务 ID：task-001
名称：项目结构创建
描述：创建 Nexus 项目的基础结构
目标关联：goal-001
项目关联：proj-001
分配 Agent：reach
状态：done
依赖：无
创建时间：2026-04-02T10:05:00Z
完成时间：2026-04-02T10:30:00Z
```

#### 1.5.4 Agent 注册

**职责描述**:
服务端提供 Agent 的注册、注销、心跳维持能力。

**核心功能**:
- **Agent 注册**：Agent 启动时向服务端注册，提交能力、状态信息
- **Agent 注销**：Agent 关闭时向服务端注销
- **心跳保持**：Agent 定期发送心跳，服务端检测 Agent 存活状态
- **状态更新**：Agent 更新自身状态（如负载、可用技能等）

**注册数据结构**:
```yaml
Agent ID：reach
名称：Reach（行动者）
能力：
  - git操作
  - 文件管理
  - 测试执行
  - 部署操作
状态：
  - 在线
  - 负载：45%
  - 当前任务：2
注册时间：2026-04-02T09:00:00Z
最后心跳：2026-04-02T10:25:00Z
```

#### 1.5.5 Agent 发现

**职责描述**:
服务端提供按能力和状态查询 Agent 的能力，用于任务分配和协作协调。

**核心功能**:
- **能力查询**：根据所需技能查询具备该技能的 Agent
- **状态查询**：查询指定状态（在线/离线/忙碌）的 Agent
- **Agent 列表**：获取满足条件的 Agent 列表，包含详细状态信息
- **负载均衡**：优先返回负载较低的 Agent

**查询示例**:
```bash
# 查询具备 git 技能的 Agent
GET /api/v1/agents?skills=git 操作

# 查询在线且负载低于 50% 的 Agent
GET /api/v1/agents?status=online&max_load=50

# 查询结果
[
  {
    "agent_id": "reach",
    "name": "Reach（行动者）",
    "skills": ["git 操作", "文件管理", "测试执行"],
    "status": "online",
    "load": 45,
    "current_tasks": 2
  }
]
```

#### 1.5.6 争议管理

**职责描述**:
服务端提供 Agent 间冲突的裁决和处理能力，解决协作过程中的争议。

**核心功能**:
- **冲突检测**：检测 Agent 间的资源冲突、任务冲突、权限冲突
- **裁决决策**：根据预设规则或 LLM 分析，做出仲裁决策
- **仲裁执行**：执行仲裁结果，协调 Agent 行为
- **冲突记录**：记录冲突事件和裁决结果，用于后续分析

**冲突类型**:
| 冲突类型 | 说明 | 裁决策略 |
|---------|------|---------|
| **资源冲突** | 多个 Agent 争夺同一资源 | 优先级仲裁、轮询分配 |
| **任务冲突** | 多个 Agent 认为自己应负责同一任务 | 技能匹配度仲裁 |
| **权限冲突** | Agent 权限不足或越权 | 权限验证、拒绝执行 |
| **状态冲突** | Agent 对任务状态认知不一致 | 以服务端状态为准 |

**仲裁流程**:
```
1. 冲突上报：Agent A → Reins（冲突报告）
2. 冲突检测：Reins 分析冲突类型
3. 裁决决策：Reins 根据规则做出裁决
4. 仲裁执行：Reins 通知相关 Agent 执行裁决
5. 冲突解决：Agent 按裁决调整行为
```

### 1.6 Agent 注册与发现机制

**Agent 与 Reins 服务端交互的核心流程**：

```
┌─────────────┐
│   Agent     │
│  (启动)     │
└─────┬───────┘
      │ 1. 注册请求
      ▼
┌─────────────────────────────────────┐
│      Reins 服务端                   │
│  ┌─────────────┐  ┌─────────────┐  │
│  │ 注册中心    │  │ 能力注册表  │  │
│  │ - Agent ID  │  │ - 技能列表  │  │
│  │ - 能力信息  │  │ - 状态信息  │  │
│  │ - 状态信息  │  │ - 心跳时间  │  │
│  └─────────────┘  └─────────────┘  │
└───────┬───────────────────────────┘
        │ 2. 注册成功
        ▼
      ┌─────────────┐
      │   Agent     │
      │  正常工作   │
      └──────┬──────┘
             │
             │ 3. 心跳保持（定期）
             ▼
        ┌─────────────┐
        │   Reins     │
        │  更新心跳   │
        └──────┬──────┘
               │
               │ 4. 任务分配时查询 Agent
               ▼
        ┌─────────────┐
        │   Agent     │
        │  发现查询   │
        └──────┬──────┘
               │
               │ 5. 返回 Agent 列表
               ▼
        ┌─────────────┐
        │   Agent     │
        │  直连通信   │
        └─────────────┘
```

#### 1.6.1 Agent 注册

**注册流程**:

1. **Agent 启动**：Agent 启动时向 Reins 服务端发送注册请求
2. **提交信息**：Agent 提交自身 ID、能力列表、状态信息
3. **服务端验证**：服务端验证 Agent 合法性，记录到注册表
4. **注册成功**：返回注册确认，Agent 进入正常运行状态

**注册请求示例**:
```json
{
  "action": "register",
  "agent": {
    "id": "reach",
    "name": "Reach（行动者）",
    "version": "1.0.0",
    "capabilities": [
      "git_operation",
      "file_management",
      "test_execution",
      "deployment"
    ],
    "status": {
      "state": "online",
      "load": 45,
      "current_tasks": 2
    },
    "heartbeat_interval": 30
  }
}
```

**注册响应示例**:
```json
{
  "status": "success",
  "message": "Agent registered successfully",
  "agent_id": "reach",
  "registered_at": "2026-04-02T09:00:00Z"
}
```

#### 1.6.2 Agent 注销

**注销流程**:

1. **正常注销**：Agent 关闭前向服务端发送注销请求
2. **异常下线**：Agent 超过心跳超时时间，服务端自动标记为离线
3. **任务转移**：注销时，服务端重新分配该 Agent 负责的任务

**注销请求示例**:
```json
{
  "action": "unregister",
  "agent_id": "reach",
  "reason": "graceful_shutdown"
}
```

#### 1.6.3 心跳保持

**心跳机制**:

- **心跳间隔**：Agent 每 30 秒向服务端发送一次心跳
- **心跳超时**：超过 90 秒未收到心跳，标记 Agent 为离线
- **心跳内容**：包含当前状态、负载、任务数等信息

**心跳请求示例**:
```json
{
  "action": "heartbeat",
  "agent_id": "reach",
  "timestamp": "2026-04-02T10:25:00Z",
  "status": {
    "state": "online",
    "load": 45,
    "current_tasks": 2
  }
}
```

#### 1.6.4 Agent 发现

**发现流程**:

1. **查询请求**：Agent 或任务调度器向服务端发送发现请求
2. **条件过滤**：根据能力、状态等条件过滤 Agent 列表
3. **返回结果**：返回符合条件的 Agent 列表及详细信息
4. **直连通信**：获取 Agent 地址后，A2A 直连通信

**发现查询示例**:
```json
{
  "action": "discover",
  "filters": {
    "skills": ["git_operation", "test_execution"],
    "status": "online",
    "max_load": 50
  }
}
```

**发现响应示例**:
```json
{
  "status": "success",
  "count": 2,
  "agents": [
    {
      "agent_id": "reach",
      "name": "Reach（行动者）",
      "capabilities": ["git_operation", "file_management", "test_execution"],
      "status": {
        "state": "online",
        "load": 45,
        "current_tasks": 2
      },
      "address": "tcp://reach:8080",
      "last_heartbeat": "2026-04-02T10:25:00Z"
    },
    {
      "agent_id": "go",
      "name": "Go（执行者）",
      "capabilities": ["test_execution", "deployment"],
      "status": {
        "state": "online",
        "load": 30,
        "current_tasks": 1
      },
      "address": "tcp://go:8080",
      "last_heartbeat": "2026-04-02T10:24:00Z"
    }
  ]
}
```

#### 1.6.5 A2A 直连通信

**通信机制**:

- **发现后直连**：Agent 通过 Reins 发现目标 Agent 后，建立 A2A 直连
- **不经中转**：通信过程不经过 Reins 服务端中转
- **协议标准**：采用 A2A 协议进行 Agent 间通信
- **状态同步**：通过 Paperclip Issue 状态进行同步

**通信流程**:
```
1. Agent A 需要任务协作
2. Agent A 向 Reins 查询具备某技能的 Agent
3. Reins 返回 Agent B 的地址信息
4. Agent A 与 Agent B 建立 A2A 直连
5. Agent A 与 Agent B 直接通信协作
6. 任务状态通过 Paperclip Issue 同步
```

### 1.4 接口标准对标

**对标标准**:
- **OpenAPI 3.0**：RESTful 接口规范
- **A2A (Agent-to-Agent)**：Agent 间通信协议
- **Issue 状态机**：基于 Paperclip 的 todo→in_progress→done

**与现有工作流引擎的差异**:

| 维度 | Apache Airflow | Argo Workflows | Nexus Reins (v1.5) |
|------|----------------|----------------|-------------------|
| 定位 | DAG 调度 | K8s 工作流 | Agent 协作框架（服务端精简） |
| AI 集成 | 弱 | 无 | 强（Agent 自治协作） |
| 编排方式 | 服务端定义 DAG | 服务端定义 Workflow | Agent 通过协作技能自行协调 |
| 多 Agent | 无 | 无 | 原生支持（A2A Hub） |
| 状态同步 | 轮询 | 轮询 | Paperclip Issue 状态 + A2A 实时通信 |
| 复杂度 | 高 | 中 | **低（职责分离）** |

---

## 2. Reins 与 Paperclip 的关系

### 2.1 Reins 基于 Paperclip

**核心关系**:

```
Reins（御） = Paperclip（骨骼）+ AI Agent（大脑）

能力对照表：
├── Paperclip（已有能力）
│   ├── Issue 管理
│   ├── 状态机
│   ├── Agent 触发
│   └── 任务执行
└── AI Agent（新增能力）
    ├── 任务分解
    ├── 智能决策
    ├── 协同编排
    └── 上下文理解
```

**能力对照表**:

| 能力维度 | Paperclip 已有能力 | Reins 新增能力 |
|---------|-------------------|---------------|
| **状态管理** | Issue 状态机：todo→in_progress→done | 工作流状态机：CREATED→PENDING→RUNNING→COMPLETED/FAILED |
| **触发机制** | heartbeat run | 定时触发 + 事件触发 + API 触发 |
| **任务执行** | 单个 Agent 技能调用 | 多 Agent 协同编排 |
| **任务分解** | 无（依赖人工创建 Issue） | LLM 驱动的任务自动分解 |
| **上下文管理** | 无 | 完整的执行上下文和上下文记忆 |
| **异常处理** | 重试机制有限 | 复杂异常处理策略（死锁检测、回滚等） |
| **调度能力** | 简单队列 | DAG 调度 + 优先级 + 依赖解析 |

### 2.2 架构背景

**设计理念**:
- **Paperclip** = 骨骼（状态机、执行层）- 提供稳定、可预测的执行框架
- **AI Agent** = 大脑（协调、推理、决策）- 提供灵活、智能的决策能力
- **Reins** = 两者融合 - 既有稳定性又有灵活性

**为什么需要融合**:

| 单一方案 | 问题 | 融合方案优势 |
|---------|------|-------------|
| 纯状态机 | 灵活性差，难以处理复杂场景 | 状态机保证稳定性 + AI 提供灵活性 |
| 纯 AI Agent | 不可预测，难以调试和追踪 | AI 智能决策 + 状态机提供可追溯性 |

### 2.3 三层结构

```
Reins 工作流引擎 - 三层架构

第 1 层：目标引擎（Goal Engine）
  - 目标分解（Goal Decomposition）
  - 任务生成（Task Generation）
  - AI 推理和规划

第 2 层：编排引擎（Orchestration Engine）
  - Agent 匹配（Agent Matching）
  - 任务分配（Task Assignment）
  - 资源调度（Resource Scheduling）

第 3 层：协作引擎（Collaboration Engine）
  - 实时通信（Real-time Communication）
  - 状态推送（Status Push）
  - 异常处理（Exception Handling）
```

#### 2.3.1 目标引擎（Goal Engine）

**职责**：将用户目标分解为可执行任务

**处理流程**:

1. 接收用户输入的目标描述
2. 进行 AI 推理和规划：
   - 理解用户意图
   - 参考历史项目模式
   - 生成任务序列
3. 输出任务分解结果

**技术实现**:
- **LLM 规划**：使用 LLM 进行任务分解
- **模板库**：预定义的项目模板和模式
- **历史学习**：参考历史成功项目

#### 2.3.2 编排引擎（Orchestration Engine）

**职责**：匹配 Agent 并分配任务

**处理流程**:

1. 接收任务列表
2. 进行 Agent 匹配和任务分配：
   - 分析任务需求
   - 查找合适 Agent
   - 分配任务
3. 输出任务分配结果

**匹配策略**:
- **能力匹配**：基于 Agent 可用技能
- **负载平衡**：考虑 Agent 当前负载
- **历史表现**：参考 Agent 过往成功率

#### 2.3.3 协作引擎（Collaboration Engine）

**职责**：Agent 间实时通信和状态同步

**通信机制**:
- **发布/订阅**：基于事件的消息传递
- **状态同步**：实时推送执行状态
- **异常通知**：错误快速传播

---

## 3. 工作流引擎设计

### 3.1 工作流状态机

#### 3.1.1 状态机设计原则

**Reins 状态机基于 Paperclip Issue 状态机**:

| 层级 | Paperclip Issue 状态 | Reins 工作流状态 | 说明 |
|------|---------------------|-----------------|------|
| **Issue 级** | todo → in_progress → done | N/A | Paperclip 已有能力，Reins 继承 |
| **工作流级** | N/A | CREATED → PENDING → RUNNING → COMPLETED/FAILED | Reins 新增能力 |
| **任务级** | 无 | 待执行 → 执行中 → 完成/失败 | Reins 新增能力 |

**状态机关系**:

```
Paperclip Issue 状态机（Reins 继承）
├── todo（待处理）
├── in_progress（进行中）
└── done（已完成）
    │
    ▼
Reins 工作流状态机（Reins 新增）
├── CREATED（创建）
├── PENDING（待执行）
├── RUNNING（执行中）
│   ├── 任务状态：todo→in_progress→done（每个任务）
│   └── 整体状态：pending→running→completed
└── COMPLETED/FAILED（完成/失败）
```

**说明**:
- Reins 的每个任务在执行时，会将其转换为 Paperclip Issue（状态为 todo）
- 任务开始执行时，Issue 状态变为 in_progress
- 任务完成时，Issue 状态变为 done
- 这样就利用了 Paperclip 已有的状态机能力，不需要重复设计

#### 3.1.2 工作流状态定义

**工作流状态流转**:

```
CREATED（创建） → PENDING（待执行） → RUNNING（执行中）
                                             │
                                             ▼
                                        COMPLETED（完成）
                                             │
                                    ┌────────┴────────┐
                                    ▼                 ▼
                              FAILED（失败）    CANCELLED（已取消）
```

#### 3.1.3 状态转换规则

**工作流状态转换**:

| 当前状态 | 可转换到 | 触发条件 |
|---------|---------|---------|
| CREATED | PENDING | 验证并调度 |
| PENDING | RUNNING | 开始执行 |
| PENDING | CANCELLED | 取消待执行 |
| RUNNING | COMPLETED | 成功完成 |
| RUNNING | FAILED | 处理失败 |
| RUNNING | CANCELLED | 取消执行中 |
| FAILED | PENDING | 重试 |

**任务状态转换（基于 Paperclip Issue 状态）**:

| 当前状态 | 可转换到 | 触发条件 |
|---------|---------|---------|
| todo | in_progress | 开始执行 |
| todo | done | 跳过任务 |
| in_progress | done | 完成任务 |
| in_progress | todo | 重试任务 |
| done | in_progress | 回退任务 |

**与 Paperclip Issue 状态的对应关系**:
- `todo` = Reins 任务待执行（对应 Paperclip Issue 的 todo）
- `in_progress` = Reins 任务执行中（对应 Paperclip Issue 的 in_progress）
- `done` = Reins 任务完成（对应 Paperclip Issue 的 done）

### 3.2 工作流定义格式

#### 3.2.1 YAML 格式

工作流定义采用 YAML 格式，包含以下核心部分：

- **版本信息**：工作流版本标识
- **基本属性**：ID、名称、描述
- **输入参数**：参数定义、类型、是否必填、默认值
- **任务定义**：任务 ID、名称、目标 Agent、技能、参数、依赖关系、重试配置
- **条件分支**：条件表达式、关联任务
- **完成后动作**：通知、回调等

**示例结构**:

工作流定义包含版本、ID、名称、描述，以及参数定义（如项目名称、模板类型）。任务定义包括初始化、配置、Git 初始化等步骤，通过依赖关系连接。条件分支支持根据参数动态决定是否执行某些任务（如测试任务）。完成后动作支持触发通知事件。

#### 3.2.2 JSON Schema 验证

工作流定义符合 JSON Schema 验证规范，确保结构正确性。验证规则包括版本、ID、任务列表等必填字段，以及参数的类型和可选性检查。

---

## 4. 复杂度管理

### 4.1 复杂度评估模型（来自审查报告风险）

**风险描述**:
- 复杂工作流难以调试和排查问题
- 循环依赖、死锁等问题难以自动检测
- 工作流版本管理和回滚机制缺失
- 大规模并发工作流时的性能瓶颈

**评估指标**:

| 指标 | 说明 | 阈值 | 风险等级 |
|------|------|------|---------|
| 节点数量 | 工作流中任务节点数 | >100 | 🟡 中 |
| 深度 | 最长执行路径长度 | >20 | 🟡 中 |
| 分支数 | 条件分支数量 | >10 | 🟢 低 |
| 并发数 | 最大并发任务数 | >50 | 🟠 严重 |
| 循环依赖 | 循环引用数量 | >0 | 🔴 高 |

### 4.2 复杂度检测工具

#### 4.2.1 静态分析

**工作流复杂度静态分析**包含以下维度：
- **节点数量**：统计工作流中任务节点总数
- **深度计算**：计算工作流最大深度（最长路径）
- **分支数量**：统计条件分支数量
- **最大并发**：计算最大并发任务数
- **循环检测**：检测是否存在循环依赖

根据各项指标，评估风险等级（低/中/高/严重），并生成警告信息。

**技术实现**:
- **依赖图构建**：基于任务依赖关系构建有向图
- **最长路径计算**：使用拓扑排序算法
- **循环检测**：使用图遍历算法检测环

#### 4.2.2 可视化复杂度图

提供工作流复杂度可视化，包含：
- **指标面板**：节点数量、深度、并发数、分支数、循环数、风险等级
- **依赖图**：可视化展示任务依赖关系

### 4.3 复杂度缓解策略

#### 4.3.1 工作流拆分

**拆分策略**:

将大型工作流拆分为多个阶段（phase），每个阶段包含相关的任务：
- **阶段 1**：初始化和配置
- **阶段 2**：开发（Git、构建、测试）
- **阶段 3**：部署

**拆分优势**:
- 每个阶段独立测试
- 更容易定位问题
- 支持分阶段部署

#### 4.3.2 死锁检测和解除

**死锁处理流程**:

1. **构建等待图**：基于当前执行状态构建任务等待关系图
2. **检测循环**：在等待图中查找循环
3. **选择牺牲任务**：选择优先级最低的任务作为牺牲品
4. **回滚牺牲任务**：回滚牺牲任务的状态
5. **通知用户**：发送死锁检测和解除通知

### 4.4 版本管理和回滚

#### 4.4.1 版本控制

**版本控制策略**:

- **版本策略**：采用语义化版本（主版本。次版本.修订版本）
- **版本历史**：记录每个版本的创建时间、创建人、变更内容、状态
- **版本状态**：支持 deprecated（已弃用）、legacy（遗留）、current（当前）状态

**版本历史示例**:

- v1.0.0：初始版本，状态已弃用
- v1.1.0：添加 lint 任务，状态遗留
- v1.2.0：优化部署、添加回滚，状态当前

#### 4.4.2 回滚机制

**回滚流程**:

1. **获取目标版本**：查询指定工作流的目标版本定义
2. **检查兼容性**：验证目标版本与当前环境的兼容性
3. **创建回滚执行**：生成回滚执行记录
4. **执行回滚**：执行回滚操作
5. **返回结果**：确认回滚成功

**兼容性检查**:
- 参数变更检查
- 任务依赖检查
- 环境依赖检查

---

## 5. 任务执行

### 5.1 执行引擎

执行引擎包含三个核心组件：

- **任务调度器**：任务队列管理、优先级处理、依赖解析
- **任务执行器**：异步执行、超时控制、异常处理
- **状态管理器**：状态持久化、状态同步、状态历史

### 5.2 任务执行流程

**标准执行流程**:

1. **任务提交**：用户提交任务
2. **验证任务**：验证参数、权限、依赖关系
3. **加入队列**：根据优先级加入任务队列
4. **获取任务**：调度器分派任务
5. **执行任务**：调用 Agent 技能执行
6. **记录结果**：记录成功/失败/异常
7. **状态更新**：触发下一步执行

### 5.3 超时和重试

#### 5.3.1 重试配置

重试配置包含以下要素：

- **最大重试次数**：默认 3 次
- **初始延迟**：默认 5 秒
- **退避倍数**：默认 2.0（指数退避）
- **最大延迟**：默认 300 秒

**重试条件**:
- 超时错误
- 连接错误
- 临时失败

**不重试的情况**:
- 验证错误
- 权限拒绝
- 资源未找到

#### 5.3.2 超时配置

超时配置包含：

- **默认超时**：默认 300 秒（5 分钟）
- **最大超时**：最大 3600 秒（1 小时）
- **技能特定超时**：针对不同技能设置特定超时时间

---

## 6. 实时通信

### 6.1 状态推送机制

**状态推送器**负责实时推送工作流状态更新：

1. **Redis 广播**：通过 Redis Pub/Sub 广播状态更新
2. **WebSocket 推送**：通过 WebSocket 推送给前端客户端
3. **事件日志**：记录审计日志

### 6.2 事件类型

**标准事件类型**:

| 事件 | 触发时机 | 数据内容 |
|------|---------|---------|
| `workflow.started` | 工作流开始 | 工作流 ID、用户、参数 |
| `task.started` | 任务开始 | 任务 ID、工作流 ID |
| `task.completed` | 任务完成 | 任务 ID、结果、耗时 |
| `task.failed` | 任务失败 | 任务 ID、错误、重试次数 |
| `workflow.completed` | 工作流完成 | 工作流 ID、总耗时、摘要 |
| `workflow.failed` | 工作流失败 | 工作流 ID、错误、阶段 |

---

## 7. API 设计

### 7.1 接口标准对标

**对标标准**:

| 标准 | 对标点 | 说明 |
|------|--------|------|
| **Apache Airflow API** | DAG 定义、调度 | 参考 Airflow 的 REST API |
| **Argo Workflows API** | 工作流定义、执行 | 兼容 Argo 的工作流 CRD |
| **Temporal API** | 工作流执行、状态查询 | 参考 Temporal 的 gRPC API |
| **OpenAPI 3.0** | 接口描述 | 所有 API 提供 OpenAPI 文档 |

### 7.2 工作流管理 API

**工作流管理接口**:

- **创建工作流**：兼容 Argo Workflow CRD 格式，支持 YAML 格式定义
- **执行工作流**：指定参数、回调通知 URL
- **查询工作流状态**：返回当前状态、进度、时间信息
- **停止工作流**：取消正在执行的工作流
- **回滚工作流**：回滚到指定版本

**与 Argo Workflows 的兼容**:
- Nexus Reins 支持 Argo 的 Workflow CRD 格式
- 提供 Argo 工作流的迁移工具
- 在 Argo 基础上增加 AI Agent 协作能力

### 7.3 复杂度分析 API

**复杂度分析接口**：
- 接收工作流定义
- 返回复杂度指标（节点数、深度、最大并发）
- 返回风险等级和警告信息

### 7.4 实时状态订阅 API

**WebSocket 接口**:
- 客户端通过 WebSocket 连接
- 订阅感兴趣的事件类型
- 接收实时状态更新消息

---

## 8. 性能指标

### 8.1 执行性能

| 指标 | P50 | P95 | P99 |
|------|-----|-----|-----|
| 任务调度延迟 | 10ms | 50ms | 100ms |
| 任务执行时间 | 500ms | 2s | 5s |
| 状态同步延迟 | 50ms | 200ms | 500ms |
| 工作流创建时间 | 100ms | 300ms | 500ms |

### 8.2 并发能力

| 指标 | 目标值 |
|------|-------|
| 并发工作流数 | 1000 |
| 并发任务数 | 10000 |
| 消息吞吐量 | 10000 msg/s |

---

## 9. 与五兄弟的协作

> **简化原则（v1.4）**：服务端（Reins）只管目标/项目/任务/Agent发现注册/争议。协作流程全部下沉到Agent端，作为Agent端本地技能/认知。

### 9.1 协作模式总览

**核心转变**：协作由 **Agent端** 发起，不经过 Reins 服务端中转。

| 协作方向 | 触发者 | 协作内容 | 通信方式 |
|---------|-------|---------|---------|
| Agent ↔ Grasp | Agent端（协作技能） | 意图理解、上下文查询 | A2A 直连 |
| Agent ↔ Reach | Agent端（协作技能） | 工具调用、技能执行 | A2A 直连 |
| Agent ↔ Evo | Agent端（协作技能） | 经验查询、模式学习 | A2A 直连 |
| Agent ↔ Vigil | Agent端（协作技能） | 安全检查、风险评估 | A2A 直连 |

**服务端职责**：
- **发现**：当 Agent 不知道谁具备某能力时，通过 Reins 查询 Agent 列表
- **注册**：Agent 启动时向 Reins 注册能力和状态
- **争议**：Agent 间协作出现冲突时，提交 Reins 裁决

### 9.2 协作流程（Agent 端视角）

#### 9.2.1 Agent → Grasp（意图理解）

```
1. Agent 需要理解任务背景
2. Agent 通过本地协作技能调用 Grasp
3. Grasp 返回意图和上下文信息
4. Agent 继续执行协作流程
```

#### 9.2.2 Agent → Reach（工具调用）

```
1. Agent 需要执行具体操作
2. Agent 通过本地协作技能调用 Reach
3. Reach 执行工具调用
4. Reach 返回执行结果
5. Agent 继续执行协作流程
```

#### 9.2.3 Agent → Evo（经验学习）

```
1. Agent 需要参考历史经验
2. Agent 通过本地协作技能查询 Evo
3. Evo 返回相关成功模式
4. Agent 优化执行策略
```

#### 9.2.4 Agent → Vigil（安全检查）

```
1. Agent 准备执行敏感操作
2. Agent 通过本地协作技能请求 Vigil 检查
3. Vigil 返回允许/拒绝及原因
4. Agent 根据结果决定是否继续
```

### 9.3 服务端与 Agent 端的边界

```
┌─────────────────────────────────────────────────────────────┐
│                     Reins 服务端                             │
│  ✅ 目标管理    ✅ 项目管理    ✅ 任务管理                    │
│  ✅ Agent 发现   ✅ Agent 注册   ✅ 争议处理                  │
│                                                             │
│  ❌ 不参与协作流程（不下沉到服务端）                          │
└─────────────────────────────────────────────────────────────┘
                              │
              服务端只提供发现/注册/争议
                              │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Agent端     │ ←──→ │  Agent端     │ ←──→ │  Agent端     │
│  (Grasp)     │ A2A  │  (工作Agent) │ A2A  │  (Reach)     │
└──────────────┘      └──────────────┘      └──────────────┘
                              │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Agent端     │ A2A  │  Agent端     │ A2A  │  Agent端     │
│  (Vigil)     │ ←──→ │  (Evo)       │ ←──→ │  (Go)        │
└──────────────┘      └──────────────┘      └──────────────┘

协作流程 = Agent 端本地技能（协作认知）
不是服务端的职责
```

### 9.4 争议处理示例

当 Agent 间协作出现冲突时：

```
1. Agent A 和 Agent B 在任务分配上产生争议
2. 任一方将争议提交 Reins 服务端
3. Reins 根据规则裁决（如：技能匹配度、负载情况）
4. Reins 通知双方执行裁决结果
5. Agent 调整行为，争议解决
```

**争议类型**：资源冲突、任务归属冲突、权限冲突、状态认知不一致

### 9.5 协作技能 = Agent 端技能

协作流程不是服务端的职责，而是每个 Agent 的**本地技能/认知**：

| Agent | 协作技能 |
|-------|---------|
| Grasp | 意图解析协作、本地知识查询 |
| Reach | 任务执行协作、工具调用协调 |
| Evo | 经验匹配协作、模式学习 |
| Vigil | 安全检查协作、风险评估 |
| Go | 工作流执行协作 |

**协作技能的调用**：
- 由 Agent 的 LLM 决策是否调用
- 根据当前任务上下文自主决定协作对象
- 不经过服务端编排

---

## 10. 复杂度管理配置示例

**复杂度管理配置**包含以下部分：

- **复杂度限制**：最大节点数、最大深度、最大分支数、最大并发数
- **死锁检测配置**：启用状态、检测间隔、自动解决策略、牺牲任务选择策略
- **版本管理配置**：启用状态、最大版本数、自动清理旧版本、保留天数
- **可视化配置**：启用状态、导出格式、是否包含指标

---

## 11. 监控与告警

### 11.1 关键指标

| 指标 | 说明 | 告警阈值 |
|------|------|---------|
| 工作流积压数 | 待执行工作流数量 | >100 |
| 平均执行时间 | 工作流平均执行时间 | >5 分钟 |
| 失败率 | 工作流失败比例 | >5% |
| 死锁检测次数 | 死锁检测频率 | >10 次/小时 |
| 复杂度告警 | 高复杂度工作流数量 | >5 |

### 11.2 审计日志

**审计日志包含**:
- 事件类型
- 工作流 ID
- 版本号
- 用户 ID
- 执行时长
- 执行任务数
- 失败任务数
- 复杂度指标
- 时间戳

---

## 14. 版本控制

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| v1.0 | 2026-04-02 | 初始版本（含融合架构和复杂度管理） | 麻子 |
| v1.2 | 2026-04-02 | 接口对标 Airflow/Argo + 补充使用场景 | 麻子 |
| v1.3 | 2026-04-02 | 明确 Reins 基于 Paperclip 关系，状态机设计基于 Paperclip Issue 状态 | 麻子 |
| v1.4 | 2026-04-02 | 简化服务端职责，引入 Human on the Loop 原则 | 麻子 |
| v1.5 | 2026-04-02 | 补充 Reins 服务端完整职责（6 大职责）及 Agent 注册与发现机制 | 麻子 |
| v1.6 | 2026-04-03 | **完善 Human on the Loop 原则，明确流程下沉到 Agent 端** | **麻子** |
| v1.7 | 2026-04-09 | **简化协作架构：服务端只管目标/项目/任务/发现注册/争议，协作流程下沉到Agent端** | **麻子** |

---

## 15. 使用场景

### 15.1 场景一：自动化部署流程

**业务场景**:用户需要通过工作流自动部署应用

**流程说明**:

1. 用户通过 Nexus Console 或 API 创建部署工作流
2. 界面层验证请求、鉴权、路由到 Reins 工作流引擎
3. Reins 分解任务：
   - 调用 Reach 的 Git 拉取技能获取代码
   - 调用 Reach 的测试运行技能执行测试
   - 调用 Reach 的云部署技能部署到云服务器
   - 调用 Vigil 进行安全检查
4. 所有步骤通过 A2A Hub 协调，状态实时推送到前端
5. 完成后 Grasp 记录本次部署经验到知识库
6. Evo 分析部署效率，优化未来部署策略

**使用 Reins 的价值**:
- 可视化工作流编排
- 实时状态同步
- 多 Agent 协作协调
- 自动回滚和重试

### 15.2 场景二：数据分析流水线

**业务场景**:定时执行数据分析任务，生成报告

**流程说明**:

1. Reins 定时触发数据分析工作流
2. 工作流分解：
   - 数据提取（Reach 数据库查询技能）
   - 数据清洗（Reach 文件系统技能）
   - 数据分析（Evo 选择分析模型）
   - 报告生成（Reach 文件系统写入技能）
   - 邮件发送（Reach 邮件技能）
3. 执行过程中实时监控状态
4. 完成后通知相关用户

**使用 Reins 的价值**:
- 支持复杂的数据处理流程
- 自动错误处理和重试
- 完整的执行审计
- 灵活的调度策略

### 15.3 场景三：CI/CD 集成

**业务场景**:集成到现有 CI/CD 流程

**流程说明**:

1. Git Push 触发 Reins 工作流
2. Reins 执行 CI/CD 流程：
   - 代码检查（lint）
   - 单元测试
   - 集成测试
   - 构建镜像
   - 部署到测试环境
   - 安全扫描（Vigil）
3. 每个步骤状态实时反馈到 Git PR
4. 部署成功后自动创建发布工单

**与 Argo Workflows 的对比**:
- Reins 支持 AI Agent 智能决策
- 更强的实时性（WebSocket vs 轮询）
- 内置五兄弟协同能力
- 更好的可扩展性

---

## 16. 参考文档

1. [00-platform-architecture.md](./00-platform-architecture.md) - 平台架构
2. [01-grasp-architecture.md](./01-grasp-architecture.md) - 悟（认知）
3. [03-evo-architecture.md](./03-evo-architecture.md) - 化（进化）
4. [nexus-arch-review-report.md](./nexus-arch-review-report.md) - 架构审查报告
5. [Paperclip GitHub](https://github.com/microsoft/paperclip) - Paperclip 项目
6. [Apache Airflow API](https://airflow.apache.org/docs/apache-airflow/stable/rest-api-ref.html)
7. [Argo Workflows](https://argoproj.github.io/workflows/)

---

**文档状态**:✅ 已完成  
**风险应对**:✅ 工作流引擎复杂度管理已补充  
**修正说明**:✅ v1.3 已明确 Reins 基于 Paperclip 关系，状态机设计基于 Paperclip Issue 状态  
**统一改写**:✅ v1.4 完成去代码改写  
**版本更新**:✅ v1.5 已补充 Reins 服务端完整职责（6 大职责）及 Agent 注册与发现机制  
**最新修正**:✅ v1.6 完善 Human on the Loop 原则，明确流程下沉到 Agent 端


---


# Nexus 调度引擎详细设计

> **日期**: 2026-05-01
> **状态**: 设计稿，待评审
> **目标**: 让 Nexus 从"被动分发器"升级为"主动调度引擎"

---

## 一、现状诊断

### 1.1 已有的调度相关组件

| 文件 | 组件 | 功能 | 状态 |
|------|------|------|------|
| `background_tasks.py` | `HeartbeatOfflineDetector` | 检测 Agent 离线（内存 registry 扫描） | ⚠️ 只检测不回收 |
| `background_tasks.py` | `SseDisconnectDetector` | SSE 断连降级到 Polling | ✅ 可用 |
| `background_tasks.py` | `TaskTimeoutDetector` | 超时任务回收 | ⚠️ 有代码但未接入启动流程 |
| `api/assignment.py` | `agent_heartbeat_with_tasks` | 心跳+任务分配 | ⚠️ 被动响应，不主动调度 |
| `services/task_validator.py` | `TaskValidator` | 任务完成结果校验 | ✅ 可用 |
| `services/task_dispatcher.py` | `TaskDispatcher` | 任务派发服务 | ⚠️ 独立于调度循环 |
| `models/task.py` | `TaskStatus` | 任务状态枚举 | ✅ 已有 7 种状态 |
| `models/task.py` | `TaskDependency` | 任务依赖表 | ✅ 表已存在 |
| `persistence/tables.py` | Agent 表 | 含 `last_heartbeat`/`status`/`load` | ⚠️ 无健康度字段 |

### 1.2 核心缺失

| 缺失项 | 说明 | 影响 |
|--------|------|------|
| **统一调度器** | 没有中央调度循环，各 Detector 各自为战 | 无法协同工作 |
| **Agent 健康度 DB 持久化** | 健康状态只在内存，重启丢失 | 无法追溯 |
| **依赖解锁机制** | 前置任务完成 → 不自动解锁后续 | DAG 执行断裂 |
| **主动任务派发** | 只在心跳时分配，不主动推送 | Agent 不来心跳就不分配 |
| **任务重新分配** | 超时回收后任务变 blocked，不重新派发 | 任务永远卡住 |
| **调度器启动集成** | Detector 没有被 server.py 启动 | 代码存在但不运行 |

---

## 二、架构设计

### 2.1 调度引擎全景

```
┌─────────────────────────────────────────────────────────┐
│                    Nexus Server (server.py)              │
│                                                         │
│   ┌───────────────────────────────────────────────────┐ │
│   │           NexusScheduler（新）                      │ │
│   │                                                   │ │
│   │  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐ │ │
│   │  │ Agent   │ │ 任务    │ │ 依赖     │ │ 结果   │ │ │
│   │  │ 健康度  │ │ 分配器  │ │ 解析器   │ │ 验证器 │ │ │
│   │  └─────────┘ └─────────┘ └──────────┘ └────────┘ │ │
│   │                                                   │ │
│   │  调度循环：每 30 秒 tick 一次                       │ │
│   │  1. 扫描 Agent 健康度                              │ │
│   │  2. 检测超时任务                                   │ │
│   │  3. 回收离线 Agent 任务                             │ │
│   │  4. 重新分配已回收任务                              │ │
│   │  5. 分配待分配任务                                  │ │
│   │  6. 解锁依赖任务                                    │ │
│   │  7. 统计报告                                       │ │
│   └───────────────────────────────────────────────────┘ │
│                                                         │
│   API 层（已有，保留）                                    │
│   /api/v1/agents/{id}/heartbeat → 被动响应              │
│   /api/v1/scheduler/stats → 新：调度状态查询             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2.2 调度循环核心逻辑

```python
class NexusScheduler:
    """
    Nexus 核心调度引擎
    
    职责：
    - 统一管理 Agent 健康度
    - 主动分配/回收/重新分配任务
    - 监控任务超时
    - 解锁依赖关系
    - 生成调度报告
    """
    
    TICK_INTERVAL = 30  # 每 30 秒执行一次
    
    # 健康度阈值（秒）
    STALE_THRESHOLD = 300      # 5 分钟无心跳 → stale
    OFFLINE_THRESHOLD = 900    # 15 分钟无心跳 → offline
    
    # 任务超时（分钟）
    TASK_TIMEOUT = 30          # 30 分钟未完成 → timeout
    
    # 重试策略
    MAX_RETRY = 3              # 最多重试 3 次
    
    def __init__(self, db_manager):
        self.db = db_manager
        self._running = False
        self._task: asyncio.Task = None
        self._stats = SchedulerStats()
    
    async def start(self):
        """启动调度循环（server.py 启动时调用）"""
        self._running = True
        self._task = asyncio.create_task(self._tick_loop())
        logger.info("[Scheduler] Started (interval=30s)")
    
    async def stop(self):
        """停止调度循环"""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("[Scheduler] Stopped")
    
    async def _tick_loop(self):
        """调度主循环"""
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"[Scheduler] Tick error: {e}")
            await asyncio.sleep(self.TICK_INTERVAL)
    
    async def _tick(self):
        """一次完整的调度周期"""
        step_results = {}
        
        # Step 1: Agent 健康度扫描
        step_results["health"] = await self._scan_agent_health()
        
        # Step 2: 超时任务回收
        step_results["timeout"] = await self._recover_timeout_tasks()
        
        # Step 3: 离线 Agent 任务回收
        step_results["recover"] = await self._recover_offline_tasks()
        
        # Step 4: 重新分配已回收任务
        step_results["reassign"] = await self._redistribute_recovered_tasks()
        
        # Step 5: 分配待分配任务
        step_results["assign"] = await self._assign_pending_tasks()
        
        # Step 6: 依赖解锁
        step_results["unlock"] = await self._unlock_dependencies()
        
        # Step 7: 更新统计
        self._stats.update(step_results)
        
        if any(v.get("changed", False) for v in step_results.values()):
            logger.info(f"[Scheduler] Tick complete: {self._stats.summary()}")
```

---

## 三、数据库变更

### 3.1 Agent 表扩展

```sql
-- 迁移脚本：migrations/014_agent_health.sql

-- 新增健康度字段
ALTER TABLE agents ADD COLUMN health_status VARCHAR(20) DEFAULT 'online';
-- online / stale / offline

-- 新增健康度时间戳
ALTER TABLE agents ADD COLUMN last_status_change DATETIME;
-- 上次状态变更时间

-- 新增连续离线次数
ALTER TABLE agents ADD COLUMN consecutive_offline_count INTEGER DEFAULT 0;
-- 用于判断是否要标记为 permanently_offline

-- 新增最大离线次数阈值
ALTER TABLE agents ADD COLUMN max_offline_before_deactivate INTEGER DEFAULT 5;
-- 超过此次数标记为 deactivated

-- 创建健康度索引
CREATE INDEX idx_agents_health_status ON agents(health_status);
CREATE INDEX idx_agents_last_heartbeat ON agents(last_heartbeat);
```

### 3.2 Agent 健康度状态机

```
                    首次注册
                       │
                       ▼
                   ┌────────┐
                   │ online │ ← 心跳正常（< 5 分钟）
                   └───┬────┘
                       │ 5 分钟无心跳
                       ▼
                   ┌────────┐
                   │ stale  │ ← 心跳可疑（5-15 分钟）
                   └───┬────┘
                       │ 15 分钟无心跳
                       ▼
                   ┌────────┐
    ┌──────────────│offline │──┐
    │ 心跳恢复      └───┬────┘  │
    ▼                   │       │ 连续 5 次
┌────────┐              │       │ 离线
│ online │              │       │
└────────┘              │       ▼
                   ┌────────┐
                   │   回   │──→ 任务回收 → deactivated
                   │   收   │
                   └────────┘
```

### 3.3 Task 表扩展

```sql
-- 迁移脚本：migrations/015_task_scheduling.sql

-- 新增超时原因字段
ALTER TABLE tasks ADD COLUMN timeout_reason TEXT;
-- 记录超时原因

-- 新增已回收标志
ALTER TABLE tasks ADD COLUMN recovery_count INTEGER DEFAULT 0;
-- 被回收重新分配的次数

-- 新增调度优先级（动态调整）
ALTER TABLE tasks ADD COLUMN schedule_priority INTEGER DEFAULT 0;
-- 基础 priority 之上的动态优先级调整
-- 值越大越优先分配

-- 新增任务分配时间
ALTER TABLE tasks ADD COLUMN assigned_at DATETIME;
-- 用于计算分配后多久未响应

-- 创建索引
CREATE INDEX idx_tasks_assigned_agent ON tasks(assigned_agent) WHERE assigned_agent IS NOT NULL;
CREATE INDEX idx_tasks_unassigned ON tasks(status) WHERE status IN ('todo', 'pending');
CREATE INDEX idx_tasks_in_progress ON tasks(status, started_at) WHERE status = 'in_progress';
```

### 3.4 新增调度日志表

```sql
-- 迁移脚本：migrations/016_scheduler_log.sql

CREATE TABLE scheduler_log (
    id TEXT PRIMARY KEY,
    tick_number INTEGER,
    action TEXT NOT NULL,
    -- assign / recover / timeout / unlock / reassign
    target_type TEXT NOT NULL,
    -- agent / task / dependency
    target_id TEXT NOT NULL,
    detail TEXT,
    -- JSON: 操作详情
    success INTEGER DEFAULT 1,
    error TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_scheduler_log_action ON scheduler_log(action);
CREATE INDEX idx_scheduler_log_target ON scheduler_log(target_type, target_id);

-- 保留最近 7 天的日志，自动清理
-- （可通过定时任务或启动时清理）
```

---

## 四、核心模块设计

### 4.1 AgentHealthManager（Agent 健康度管理）

**文件**: `reins/scheduler/health_manager.py`（新建）

```python
class AgentHealthManager:
    """
    Agent 健康度管理器
    
    职责：
    1. 扫描所有 Agent 的 last_heartbeat
    2. 根据时间阈值更新 health_status
    3. 状态变更时触发相应动作
    4. 更新 DB（持久化健康度）
    """
    
    def scan(self) -> dict:
        """
        执行一次健康度扫描
        
        返回：
        {
            "online_count": 10,
            "stale_count": 2,
            "offline_count": 1,
            "transitions": [
                {"agent_id": "xxx", "from": "online", "to": "stale"},
                {"agent_id": "yyy", "from": "stale", "to": "offline"},
            ],
            "changed": True/False
        }
        """
        pass
    
    def on_heartbeat(self, agent_id: str):
        """
        Agent 发心跳时调用
        
        动作：
        1. 更新 last_heartbeat
        2. 如果当前是 stale/offline → 恢复为 online
        3. 重置 consecutive_offline_count
        4. 触发任务重新分配（如果之前有被回收的任务）
        """
        pass
    
    def get_offline_agents(self) -> list[str]:
        """返回所有 offline Agent ID"""
        pass
    
    def get_stale_agents(self) -> list[str]:
        """返回所有 stale Agent ID"""
        pass
```

### 4.2 TaskRecoverer（任务回收器）

**文件**: `reins/scheduler/task_recoverer.py`（新建）

```python
class TaskRecoverer:
    """
    任务回收器
    
    职责：
    1. 回收 offline Agent 的任务
    2. 回收超时的 in_progress 任务
    3. 标记任务为 recoverable 状态
    4. 记录回收原因
    """
    
    def recover_from_offline(self, agent_id: str) -> list[str]:
        """
        回收指定 offline Agent 的所有任务
        
        逻辑：
        1. 找到 assigned_agent = agent_id 且 status IN (todo, pending, in_progress) 的任务
        2. 更新 assigned_agent = NULL, status = todo, recovery_count += 1
        3. 写入 scheduler_log
        4. 减少 Agent 的 current_tasks
        
        返回：被回收的任务 ID 列表
        """
        pass
    
    def recover_from_timeout(self, timeout_minutes: int = 30) -> list[str]:
        """
        回收所有超时的 in_progress 任务
        
        逻辑：
        1. 找到 status = in_progress AND started_at < (now - timeout_minutes) 的任务
        2. 更新 status = timeout, timeout_reason = "执行超时"
        3. 写入 task_failure_log
        4. 减少 Agent 的 current_tasks
        
        返回：被回收的任务 ID 列表
        """
        pass
    
    def recover_single(self, task_id: str, reason: str) -> bool:
        """手动回收单个任务"""
        pass
```

### 4.3 TaskAssigner（任务分配器）

**文件**: `reins/scheduler/task_assigner.py`（新建）

```python
class TaskAssigner:
    """
    任务分配器
    
    职责：
    1. 从待分配队列中取任务
    2. 按能力/负载匹配 Agent
    3. 执行分配（写 DB）
    4. 记录分配日志
    """
    
    def assign_pending_tasks(self, max_per_tick: int = 10) -> dict:
        """
        分配待分配任务
        
        逻辑：
        1. 查询 status IN (todo, pending) AND assigned_agent IS NULL 的任务
        2. 按 priority DESC + schedule_priority DESC + created_at ASC 排序
        3. 查询所有 online/stale Agent（排除 offline）
        4. 对每个任务：
           a. 过滤能处理该任务的 Agent（能力匹配）
           b. 按负载排序（load + current_tasks * 10）
           c. 分配给负载最低的 Agent
           d. 更新 DB：assigned_agent, status = in_progress, assigned_at = now
           e. 增加 Agent 的 current_tasks
        
        返回：
        {
            "assigned_count": 5,
            "assignments": [
                {"task_id": "xxx", "agent_id": "guzi"},
                ...
            ],
            "skipped": 2,  # 无可用 Agent
            "changed": True/False
        }
        """
        pass
    
    def redistribute_recovered(self, max_per_tick: int = 5) -> dict:
        """
        重新分配被回收的任务
        
        与 assign_pending_tasks 的区别：
        - 专门处理 recovery_count > 0 的任务
        - 检查 retry_count < max_retries（超过则标记 failed）
        - 排除上次分配的 Agent（避免分配给同一个导致循环超时）
        """
        pass
```

### 4.4 DependencyResolver（依赖解析器）

**文件**: `reins/scheduler/dependency_resolver.py`（新建）

```python
class DependencyResolver:
    """
    依赖解析器
    
    职责：
    1. 当任务完成时，检查是否有依赖它的任务
    2. 如果依赖全部满足 → 解锁后续任务
    3. 如果依赖未满足 → 保持 blocked/todo
    """
    
    def unlock_on_completion(self, completed_task_id: str) -> list[str]:
        """
        当任务完成时调用
        
        逻辑：
        1. 查询 task_dependencies 中 dependency_id = completed_task_id 的记录
        2. 对每个依赖该任务的 task：
           a. 检查该 task 的所有依赖是否都已完成
           b. 如果全部完成 → 更新 status = todo（从 blocked 或 pending 恢复）
           c. 记录解锁日志
        
        返回：被解锁的任务 ID 列表
        """
        pass
    
    def check_all_dependencies_met(self, task_id: str) -> bool:
        """检查指定任务的所有依赖是否已完成"""
        pass
    
    def get_blocked_tasks(self) -> list[str]:
        """返回所有被阻塞的任务 ID"""
        pass
```

### 4.5 ResultVerifier（结果验证器）

**文件**: `reins/scheduler/result_verifier.py`（新建）

```python
class ResultVerifier:
    """
    结果验证器
    
    职责：
    1. 验证 Agent 上报的任务结果
    2. 校验通过后标记 done
    3. 校验失败转 review_needed
    4. 触发依赖解锁
    """
    
    def verify(self, task_id: str, result: dict) -> dict:
        """
        验证任务结果
        
        校验规则（复用现有 TaskValidator）：
        1. 结果非空
        2. 结果长度 >= 10
        3. 结果包含类别关键词
        
        校验通过：
        1. status = done, completed_at = now
        2. 减少 Agent current_tasks
        3. 触发依赖解锁（DependencyResolver.unlock_on_completion）
        
        校验失败：
        1. status = review_needed
        2. 记录 error_message
        3. 通知用户审核
        
        返回：
        {
            "task_id": "xxx",
            "passed": True/False,
            "action": "done" / "review_needed",
            "unlocked_tasks": ["yyy", "zzz"]  # 如果有
        }
        """
        pass
```

### 4.6 SchedulerStats（调度统计）

**文件**: `reins/scheduler/stats.py`（新建）

```python
class SchedulerStats:
    """
    调度统计
    
    每 tick 更新一次，提供调度状态概览
    """
    
    total_ticks: int = 0
    last_tick_at: datetime = None
    
    # Agent 统计
    online_agents: int = 0
    stale_agents: int = 0
    offline_agents: int = 0
    
    # 任务统计
    total_tasks: int = 0
    todo_tasks: int = 0
    in_progress_tasks: int = 0
    done_tasks: int = 0
    blocked_tasks: int = 0
    timeout_tasks: int = 0
    
    # 本次 tick 动作统计
    assigned_this_tick: int = 0
    recovered_this_tick: int = 0
    unlocked_this_tick: int = 0
    
    # 累计统计
    total_assigned: int = 0
    total_recovered: int = 0
    total_unlocked: int = 0
    
    def update(self, step_results: dict):
        """从 step 结果更新统计"""
        pass
    
    def summary(self) -> str:
        """生成统计摘要字符串"""
        return (
            f"agents: {self.online_agents}online/{self.stale_agents}stale/{self.offline_agents}offline | "
            f"tasks: {self.todo_tasks}todo/{self.in_progress_tasks}progress/{self.done_tasks}done | "
            f"tick: assigned={self.assigned_this_tick} recovered={self.recovered_this_tick}"
        )
    
    def to_dict(self) -> dict:
        """转为 dict（给 API 使用）"""
        pass
```

---

## 五、文件结构与集成

### 5.1 新建文件清单

```
packages/server/src/reins/scheduler/
├── __init__.py          # 导出 NexusScheduler
├── core.py              # NexusScheduler 主类（调度循环）
├── health_manager.py    # AgentHealthManager
├── task_recoverer.py    # TaskRecoverer
├── task_assigner.py     # TaskAssigner
├── dependency_resolver.py # DependencyResolver
├── result_verifier.py   # ResultVerifier
└── stats.py             # SchedulerStats
```

### 5.2 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `api/server.py` | 启动时初始化并启动 NexusScheduler；关闭时停止 |
| `models/task.py` | 新增 timeout_reason, recovery_count, schedule_priority, assigned_at 字段 |
| `persistence/tables.py` | Agent 表新增 health_status 等字段 |
| `api/assignment.py` | 心跳时调用 `health_manager.on_heartbeat()` |
| `background_tasks.py` | 保留 HeartbeatOfflineDetector 和 SseDisconnectDetector（兼容），但调度职责移交 NexusScheduler |

### 5.3 server.py 集成点

```python
# server.py 的 create_app 函数中：

from reins.scheduler.core import NexusScheduler

def create_app(...):
    app = FastAPI()
    
    # ... 现有初始化 ...
    
    # 创建调度器
    scheduler = NexusScheduler(db_manager=get_db_manager())
    
    # 注册为 app 状态
    app.state.scheduler = scheduler
    
    # 启动时启动调度器
    @app.on_event("startup")
    async def startup():
        # ... 现有启动逻辑 ...
        await scheduler.start()
        logger.info("[Server] Scheduler started")
    
    # 关闭时停止调度器
    @app.on_event("shutdown")
    async def shutdown():
        # ... 现有关闭逻辑 ...
        await scheduler.stop()
        logger.info("[Server] Scheduler stopped")
    
    # 新增调度状态查询 API
    @app.get("/api/v1/scheduler/stats")
    def get_scheduler_stats():
        return app.state.scheduler.stats.to_dict()
    
    return app
```

### 5.4 心跳端点增强

```python
# api/assignment.py 的 agent_heartbeat_with_tasks 中：

@router.post("/agents/{agent_id}/heartbeat")
def agent_heartbeat_with_tasks(agent_id: str, ...):
    # 原有逻辑...
    
    # 新增：通知健康度管理器
    from reins.scheduler import get_scheduler
    scheduler = get_scheduler()
    if scheduler:
        scheduler.health_manager.on_heartbeat(agent_id)
    
    # 返回结果...
```

---

## 六、调度状态查询 API

### 6.1 调度概览

```
GET /api/v1/scheduler/stats
```

**响应**：
```json
{
  "total_ticks": 1234,
  "last_tick_at": "2026-05-01T06:00:00",
  "agents": {
    "online": 8,
    "stale": 2,
    "offline": 1
  },
  "tasks": {
    "total": 50,
    "todo": 10,
    "in_progress": 15,
    "done": 20,
    "blocked": 3,
    "timeout": 2
  },
  "this_tick": {
    "assigned": 3,
    "recovered": 1,
    "unlocked": 2
  },
  "total_actions": {
    "assigned": 500,
    "recovered": 45,
    "unlocked": 120
  }
}
```

### 6.2 Agent 健康度

```
GET /api/v1/scheduler/agents/health
```

**响应**：
```json
[
  {
    "id": "guzi",
    "name": "谷子",
    "health_status": "online",
    "last_heartbeat": "2026-05-01T05:59:00",
    "last_status_change": "2026-05-01T05:00:00",
    "consecutive_offline_count": 0,
    "current_tasks": 5,
    "load": 30
  },
  {
    "id": "wenzi",
    "name": "蚊子",
    "health_status": "stale",
    "last_heartbeat": "2026-05-01T05:50:00",
    "last_status_change": "2026-05-01T05:55:00",
    "consecutive_offline_count": 0,
    "current_tasks": 0,
    "load": 0
  }
]
```

### 6.3 调度日志

```
GET /api/v1/scheduler/logs?action=assign&page=1&page_size=20
```

**响应**：
```json
{
  "items": [
    {
      "id": "log-xxx",
      "tick_number": 1234,
      "action": "assign",
      "target_type": "task",
      "target_id": "task-7436736c8dd9",
      "detail": {"agent_id": "guzi", "priority": "high"},
      "success": 1,
      "error": null,
      "created_at": "2026-05-01T06:00:00"
    }
  ],
  "total": 5000,
  "page": 1,
  "page_size": 20
}
```

### 6.4 手动触发

```
POST /api/v1/scheduler/tick
```
手动触发一次调度周期（调试用）

```
POST /api/v1/scheduler/tasks/recover-timeout
```
手动触发超时回收

```
POST /api/v1/scheduler/dependencies/unlock
```
手动触发依赖解锁扫描

---

## 七、实施计划

### Phase 1: 基础设施（2 天）

| 任务 | 文件 | 说明 |
|------|------|------|
| 1.1 | `scheduler/__init__.py` | 包结构 + 全局调度器实例 |
| 1.2 | `scheduler/stats.py` | 统计类 |
| 1.3 | DB 迁移 014-016 | Agent 健康度 + Task 扩展 + 调度日志表 |
| 1.4 | `api/server.py` | 集成调度器启动/停止 |

### Phase 2: 核心调度（3 天）

| 任务 | 文件 | 说明 |
|------|------|------|
| 2.1 | `scheduler/health_manager.py` | Agent 健康度扫描 + 状态管理 |
| 2.2 | `scheduler/task_recoverer.py` | 超时/离线任务回收 |
| 2.3 | `scheduler/task_assigner.py` | 任务分配 + 重新分配 |
| 2.4 | `scheduler/core.py` | 调度主循环 |
| 2.5 | `api/assignment.py` | 心跳集成健康度管理 |

### Phase 3: 依赖与验证（2 天）

| 任务 | 文件 | 说明 |
|------|------|------|
| 3.1 | `scheduler/dependency_resolver.py` | 依赖解锁 |
| 3.2 | `scheduler/result_verifier.py` | 结果验证 |
| 3.3 | API: `/scheduler/stats` 等 4 个端点 | 调度状态查询 |
| 3.4 | 端到端测试 | 完整调度循环验证 |

### Phase 4: 优化与打磨（1 天）

| 任务 | 说明 |
|------|------|
| 日志自动清理 | scheduler_log 表 7 天过期清理 |
| 配置化 | 阈值、间隔等可配置 |
| 监控面板 | 前端展示调度状态 |
| 性能优化 | 批量 SQL、索引优化 |

---

## 八、与场景库任务的关系

调度器上线后，场景库 Sprint 49 的任务将自动受益：

```
调度器启动
  → 发现 5 个 P0 任务（task-7436736c8dd9 等）已分配给 guzi
  → guzi 心跳正常 → 继续等待执行
  → 如果 guzi 超时离线 → 自动回收任务
  → 重新分配给 mazi（麻子）
  → 麻子领任务 → 执行 → 上报完成
  → 调度器验证结果 → 标记 done
  → 解锁后续依赖任务
```

**调度器是场景库任务能真正被执行的必要条件**。

---

## 九、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 调度循环异常导致 DB 死锁 | 服务不可用 | 每个 tick 用独立事务；异常时 rollback |
| Agent 频繁上下线导致任务反复分配 | 执行效率低 | consecutive_offline_count 阈值控制 |
| 任务依赖循环（A→B→A） | 死锁 | 启动时检测 DAG 循环，拒绝非法依赖 |
| 大量任务同时可分配 | 调度慢 | max_per_tick 限制，分批处理 |
| SQLite 并发限制 | 写入冲突 | 用 begin() 事务；考虑 WAL 模式 |

---

*设计稿完成 — 2026-05-01 06:05*
