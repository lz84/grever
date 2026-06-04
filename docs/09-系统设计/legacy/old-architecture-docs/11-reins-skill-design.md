# Nexus Reins Skill 接口设计

**版本**: v1.0
**作者**: 麻子
**日期**: 2026-04-04
**状态**: 初稿

---

## 1. 概述

**Reins Skill** 是 Nexus Agent SDK 中协同驾驭系统的对外接口封装，提供 task/create、task/decompose、agent/invoke 三个核心接口。Agent 通过这些接口将任务分解、子任务分配、跨 Agent 协作等能力内化为自身可调用的技能。

### 1.1 设计背景

根据 Agent SDK 架构原则：
- SDK 和技能的出入口 **必须是 Agent**，不接受外部直接 API 调用
- 技能是 Agent 端组件，没有独立网络 API，必须通过 Agent 方法调用
- Reins Skill 封装协同驾驭能力，供 Agent 内部调用

Reins Skill 与 Grasp Skill 的关系：
- **Grasp** 提供认知能力（inject/retrieve/update）
- **Reins** 提供任务编排能力（task/create、task/decompose、agent/invoke）
- Reins Skill 可在执行过程中调用 Grasp Skill 获取领域认知

### 1.2 与 MCP 协议的关系

Reins Skill 遵循 MCP 协议规范，提供标准的工具接口：

| MCP 概念 | Reins Skill 实现 |
|---------|----------------|
| Tool | task_create / task_decompose / agent_invoke |
| Resource | 任务条目（TaskItem）、执行状态（ExecutionStatus） |
| Prompt | 任务模板（预定义分解模式） |

---

## 2. 接口设计

### 2.1 task_create - 任务创建

创建一个新的任务。

**方法签名**:

```
task_create(task: TaskInput) -> TaskCreateResult
```

**输入参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 任务标题 |
| description | string | 是 | 任务描述 |
| goal_id | string | 否 | 所属目标 ID |
| project_id | string | 否 | 所属项目 ID |
| priority | enum | 否 | P0/P1/P2，默认 P1 |
| deadline | timestamp | 否 | 截止时间 |
| parent_task_id | string | 否 | 父任务 ID（子任务时必填） |
| required_capabilities | string[] | 否 | 所需能力列表（已废弃，请使用 capability_tags） |
| estimated_hours | number | 否 | 预估工时（小时） |
| metadata | object | 否 | 附加元数据 |
| **depends_on** | **string[]** | **是** | **前置任务 ID 列表，DAG 执行顺序，无依赖则 `[]`** |
| **capability_tags** | **object** | **是** | **四维能力标签 `{"technical":[], "professional":[], "business":[], "management":[]}`** |

**返回结果**:

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | string | 任务 ID |
| status | enum | created（已创建） |
| created_at | timestamp | 创建时间 |
| parent_task_id | string | 父任务 ID |

**内部流程**:

1. **格式验证** - 检查 title、description 长度和编码
2. **权限检查** - 确认调用者有创建任务的权限
3. **写入存储** - 写入任务存储（SQLite/PostgreSQL）
4. **返回结果** - 返回 task_id 和状态

**错误码**:

| 错误码 | 说明 |
|--------|------|
| INVALID_TITLE | 标题格式无效 |
| INVALID_DESCRIPTION | 描述格式无效 |
| PARENT_NOT_FOUND | 父任务不存在 |
| PERMISSION_DENIED | 无创建权限 |
| STORAGE_ERROR | 存储写入失败 |
| **MISSING_DEPENDS_ON** | **depends_on 必填，不得为空或省略** |
| **MISSING_CAPABILITY_TAGS** | **capability_tags 必填，四维标签字典** |
| **INVALID_CAPABILITY_TAGS** | **capability_tags 包含无效维度，有效：`business/professional/technical/management`** |

---

## 附录：C（2026-05-20 新增）

### C.1 任务创建三条铁律

**铁律一：depends_on 必须设置**
- 作用：明确 DAG 执行顺序，防止并行乱序
- 值：前置任务 ID 列表，无依赖则 `[]`
- 不设置 → API 400 拒绝

**铁律二：capability_tags 必须设置**
- 作用：匹配引擎的输入，决定哪个 Agent 执行
- 值：四维标签对象 `{business:[], professional:[], technical:[], management:[]}`
- 不设置 → API 400 拒绝

**铁律三：assigned_agent 由匹配引擎决定**
- 创建时不指定 `assigned_agent`，留空
- 匹配引擎根据 `capability_tags` + 负载 + 在线状态自动分配
- 禁止在 CRUD 接口中写分配逻辑

---

### 2.2 task_decompose - 任务分解

将一个任务分解为子任务，并识别依赖关系。

**方法签名**:

```
task_decompose(task_id: string, options?: DecomposeOptions) -> TaskDecomposeResult
```

**输入参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 要分解的任务 ID |
| strategy | enum | 否 | 分解策略：auto（自动）/ conservative（保守）/ aggressive（激进），默认 auto |
| max_depth | number | 否 | 最大分解深度，默认 3 |
| min_granularity_hours | number | 否 | 最小粒度（小时），默认 1 |
| max_granularity_hours | number | 否 | 最大粒度（小时），默认 4 |
| use_grasp | boolean | 否 | 是否调用 Grasp 获取认知辅助分解，默认 true |

**DecomposeOptions 扩展**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| constraints | string[] | 否 | 约束条件列表 |
| available_agents | string[] | 否 | 可用 Agent 列表 |
| grasp_context | object | 否 | Grasp 调用上下文（type/tags/query） |

**返回结果**:

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | string | 原任务 ID |
| subtasks | Subtask[] | 子任务列表 |
| dependencies | Dependency[] | 依赖关系列表 |
| decomposition_depth | number | 分解深度 |
| estimated_total_hours | number | 总预估工时 |

**Subtask 结构**:

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | string | 子任务 ID |
| title | string | 任务标题 |
| description | string | 任务描述 |
| priority | enum | 优先级 P0/P1/P2 |
| estimated_hours | number | 预估工时 |
| granularity_hours | number | 粒度（1-4小时） |
| required_capabilities | string[] | 所需能力 |
| can_parallel_with | string[] | 可并行执行的任务 ID 列表 |
| depends_on | string[] | 依赖的任务 ID 列表 |

**Dependency 结构**:

| 字段 | 类型 | 说明 |
|------|------|------|
| from_task_id | string | 依赖方任务 ID |
| to_task_id | string | 被依赖方任务 ID |
| dependency_type | enum | finish_to_start（结束到开始）/ start_to_start（开始到开始） |

**内部流程**:

1. **任务查询** - 获取原任务的 description 和上下文
2. **Grasp 认知增强**（可选）- 调用 Grasp retrieve 获取相关领域认知
3. **LLM 分解** - 调用 LLM 进行任务分解
4. **粒度校验** - 确保每个子任务粒度在 1-4 小时范围
5. **依赖关系识别** - 分析子任务间的依赖关系
6. **并行性优化** - 识别可并行执行的任务
7. **创建子任务** - 调用 task_create 批量创建子任务
8. **返回结果** - 返回分解结果

**错误码**:

| 错误码 | 说明 |
|--------|------|
| TASK_NOT_FOUND | 任务不存在 |
| DECOMPOSE_FAILED | 分解失败 |
| GRANULARITY_VIOLATION | 粒度不符合要求 |
| GRASP_ERROR | Grasp 调用失败 |
| LLM_ERROR | LLM 调用失败 |

---

### 2.3 agent_invoke - Agent 调用

调用指定的 Agent 执行任务。

**方法签名**:

```
agent_invoke(request: AgentInvokeRequest) -> AgentInvokeResult
```

**输入参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agent_id | string | 是 | 要调用的 Agent ID |
| task_id | string | 是 | 关联的任务 ID |
| instruction | string | 是 | 给 Agent 的指令 |
| context | object | 否 | 调用上下文 |
| timeout_ms | number | 否 | 超时时间（毫秒），默认 300000（5分钟） |
| retry_on_failure | boolean | 否 | 失败时是否重试，默认 true |
| max_retries | number | 否 | 最大重试次数，默认 3 |
| grasp_enabled | boolean | 否 | 是否允许 Agent 调用 Grasp，默认 true |

**context 结构**:

| 字段 | 类型 | 说明 |
|------|------|------|
| project_id | string | 项目 ID |
| goal_id | string | 目标 ID |
| parent_task_id | string | 父任务 ID |
| available_tools | string[] | 可用工具列表 |
| constraints | string[] | 约束条件 |

**返回结果**:

| 字段 | 类型 | 说明 |
|------|------|------|
| invoke_id | string | 调用 ID |
| agent_id | string | 被调用的 Agent ID |
| task_id | string | 关联的任务 ID |
| status | enum | running（执行中）/ completed（完成）/ failed（失败）/ timeout（超时） |
| result | object | 执行结果 |
| output | string | 文本输出 |
| error | string | 错误信息 |
| duration_ms | number | 执行耗时（毫秒） |
| grasp_calls | GraspCall[] | Grasp 调用记录 |

**result 结构**:

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 是否成功 |
| output | string | 文本输出 |
| artifacts | Artifact[] | 产物列表 |
| subtasks_completed | number | 完成的子任务数 |

**Artifact 结构**:

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 产物名称 |
| type | enum | file/document/data |
| path | string | 产物路径 |
| size_bytes | number | 大小（字节） |

**GraspCall 结构**:

| 字段 | 类型 | 说明 |
|------|------|------|
| call_id | string | 调用 ID |
| method | enum | inject/retrieve/update |
| input | object | 输入参数 |
| output | object | 输出结果 |
| duration_ms | number | 调用耗时 |

**内部流程**:

1. **Agent 发现** - 从 Agent 注册表查找目标 Agent
2. **能力匹配** - 确认 Agent 具备 required_capabilities
3. **任务锁定** - 锁定任务状态防止并发冲突
4. **Grasp 上下文注入**（可选）- 若 grasp_enabled=true，注入相关领域认知
5. **执行调用** - 通过 Agent 适配器调用目标 Agent
6. **结果收集** - 收集执行结果和 Grasp 调用记录
7. **任务更新** - 更新任务状态为 completed/failed
8. **返回结果** - 返回调用结果

**错误码**:

| 错误码 | 说明 |
|--------|------|
| AGENT_NOT_FOUND | Agent 不存在 |
| AGENT_OFFLINE | Agent 不在线 |
| CAPABILITY_MISMATCH | Agent 能力不匹配 |
| TASK_LOCKED | 任务已被其他调用锁定 |
| INVOKE_TIMEOUT | 调用超时 |
| AGENT_ERROR | Agent 执行错误 |
| GRASP_ERROR | Grasp 调用失败 |

---

## 3. 数据模型

### 3.1 任务状态

| 状态 | 说明 | 可操作 |
|------|------|--------|
| created | 已创建 | 可分解、可调用 |
| decomposed | 已分解 | 可调用 |
| running | 执行中 | 等待完成 |
| completed | 已完成 | 归档 |
| failed | 失败 | 可重试、可放弃 |
| blocked | 阻塞 | 等待依赖解除 |
| cancelled | 已取消 | 归档 |

### 3.2 Agent 调用状态

| 状态 | 说明 |
|------|------|
| pending | 等待调度 |
| running | 执行中 |
| completed | 成功完成 |
| failed | 执行失败 |
| timeout | 超时 |
| cancelled | 已取消 |

### 3.3 存储结构

**本地存储**:

```
memory/reins/
├── tasks.jsonl           # 任务条目（追加模式）
├── task_dependencies.jsonl  # 依赖关系
├── invoke_history.jsonl  # 调用历史
└── index/               # 任务索引
```

---

## 4. 与 MCP 协议的对应

### 4.1 工具定义

Reins Skill 的三个接口作为 MCP Tool 对外提供：

```json
{
  "tools": [
    {
      "name": "reins_task_create",
      "description": "创建一个新任务",
      "inputSchema": {
        "type": "object",
        "properties": {
          "title": { "type": "string" },
          "description": { "type": "string" },
          "goal_id": { "type": "string" },
          "project_id": { "type": "string" },
          "priority": { "enum": ["P0", "P1", "P2"] },
          "deadline": { "type": "string", "format": "date-time" },
          "parent_task_id": { "type": "string" },
          "required_capabilities": { "type": "array", "items": { "type": "string" } },
          "estimated_hours": { "type": "number" }
        },
        "required": ["title", "description"]
      }
    },
    {
      "name": "reins_task_decompose",
      "description": "将任务分解为子任务",
      "inputSchema": {
        "type": "object",
        "properties": {
          "task_id": { "type": "string" },
          "strategy": { "enum": ["auto", "conservative", "aggressive"] },
          "max_depth": { "type": "number", "default": 3 },
          "min_granularity_hours": { "type": "number", "default": 1 },
          "max_granularity_hours": { "type": "number", "default": 4 },
          "use_grasp": { "type": "boolean", "default": true }
        },
        "required": ["task_id"]
      }
    },
    {
      "name": "reins_agent_invoke",
      "description": "调用指定 Agent 执行任务",
      "inputSchema": {
        "type": "object",
        "properties": {
          "agent_id": { "type": "string" },
          "task_id": { "type": "string" },
          "instruction": { "type": "string" },
          "context": { "type": "object" },
          "timeout_ms": { "type": "number", "default": 300000 },
          "retry_on_failure": { "type": "boolean", "default": true },
          "max_retries": { "type": "number", "default": 3 },
          "grasp_enabled": { "type": "boolean", "default": true }
        },
        "required": ["agent_id", "task_id", "instruction"]
      }
    }
  ]
}
```

### 4.2 资源定义

任务和执行状态作为 MCP Resource 对外暴露：

```json
{
  "resources": [
    {
      "uri": "reins://task/{id}",
      "name": "任务条目",
      "mimeType": "application/json"
    },
    {
      "uri": "reins://tasks",
      "name": "任务列表",
      "mimeType": "application/json"
    },
    {
      "uri": "reins://invoke/{id}",
      "name": "调用记录",
      "mimeType": "application/json"
    }
  ]
}
```

---

## 5. 调用示例

### 5.1 创建任务

```javascript
// Agent 内部调用
const result = await agent.reins.task_create({
  title: "实现用户登录功能",
  description: "在前端实现用户登录页面，包括用户名密码验证和会话管理",
  goal_id: "goal-001",
  project_id: "project-001",
  priority: "P0",
  deadline: "2026-04-10T18:00:00Z",
  required_capabilities: ["frontend", "auth"],
  estimated_hours: 8
});
// result.task_id = "task-xxx"
// result.status = "created"
```

### 5.2 分解任务

```javascript
// Agent 内部调用（自动粒度 1-4 小时）
const result = await agent.reins.task_decompose("task-xxx", {
  strategy: "auto",
  max_depth: 3,
  min_granularity_hours: 1,
  max_granularity_hours: 4,
  use_grasp: true,
  grasp_context: {
    query: "前端登录功能实现",
    type: ["pattern", "lesson"],
    tags: ["frontend", "auth"]
  }
});
// result.subtasks = [...]
// result.dependencies = [...]
// result.estimated_total_hours = 8
```

### 5.3 调用 Agent

```javascript
// Agent 内部调用
const result = await agent.reins.agent_invoke({
  agent_id: "coder",
  task_id: "subtask-001",
  instruction: "实现前端登录页面，使用 React 和 TailwindCSS",
  context: {
    project_id: "project-001",
    constraints: ["必须使用 TypeScript", "响应式设计"],
    available_tools: ["file_read", "file_write", "code_review"]
  },
  timeout_ms: 600000,
  grasp_enabled: true
});
// result.status = "completed"
// result.output = "登录页面已实现..."
// result.grasp_calls = [...]
```

---

## 6. 错误处理

### 6.1 错误响应格式

```json
{
  "error": {
    "code": "AGENT_OFFLINE",
    "message": "目标 Agent 不在线，无法调用",
    "details": {
      "agent_id": "coder",
      "last_heartbeat": "2026-04-04T07:00:00Z"
    }
  }
}
```

### 6.2 重试策略

| 错误类型 | 重试策略 |
|---------|---------|
| AGENT_OFFLINE | 指数退避，最多 5 次 |
| INVOKE_TIMEOUT | 指数退避，最多 max_retries 次 |
| TASK_LOCKED | 等待后重试，最多 3 次 |
| STORAGE_ERROR | 指数退避，最多 3 次 |
| GRASP_ERROR | 不重试，返回错误 |

---

## 7. Grasp 集成

### 7.1 task_decompose 中的 Grasp 调用

在 task_decompose 过程中，Reins Skill 可调用 Grasp 获取领域认知，辅助 LLM 进行更准确的任务分解：

```
Reins.task_decompose(task_id)
    │
    ├─→ Grasp.retrieve({
    │      query: <task.description>,
    │      type: ["pattern", "lesson"],
    │      tags: <task.required_capabilities>
    │    })
    │    │
    │    └─→ 返回相关认知条目（最佳实践、分解模式等）
    │
    └─→ LLM 分解（结合 Grasp 认知上下文）
```

### 7.2 agent_invoke 中的 Grasp 注入

在调用 Agent 前，Reins Skill 可注入相关领域认知，帮助 Agent 更好地理解任务上下文：

```
Reins.agent_invoke(agent_id, task_id, instruction)
    │
    ├─→ Grasp.retrieve({
    │      query: <instruction>,
    │      type: ["fact", "pattern"],
    │      limit: 5
    │    })
    │    │
    │    └─→ 返回相关认知，注入 Agent context
    │
    └─→ Agent 执行（带有 Grasp 认知上下文）
```

---

## 8. 与 Reins 架构的关系

### 8.1 接口层 vs 服务端

Reins Skill 是 **Agent 端**的接口封装，对应 Reins 架构中的**协作技能**层：

| 层级 | Reins 架构 | Reins Skill 接口 |
|------|-----------|----------------|
| 服务端 | Nexus Server（任务分发、争议处理） | - |
| Agent 端 | 协作技能（Reins Skill） | task_create / task_decompose / agent_invoke |
| Agent 端 | 本地技能/认知 | Grasp Skill |

### 8.2 服务端任务管理 vs Agent 端技能

| 能力 | 服务端 (Nexus Server) | Agent 端 (Reins Skill) |
|------|---------------------|----------------------|
| 任务创建 | ✅ 持久化存储 | ✅ 本地快捷创建 |
| 任务分解 | ❌ | ✅ LLM + Grasp |
| Agent 调用 | ❌ | ✅ 协调执行 |
| 状态同步 | ✅ 统一视图 | ✅ 本地优先 |

---

## 9. 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-04-04 | 初始版本，包含 task_create、task_decompose、agent_invoke 三个接口 |

---

## 10. 待明确事项

1. **Agent 注册表位置** - Agent 发现机制的具体实现（本地注册表 / 服务端查询）
2. **跨 Agent 调用协议** - Agent 间通信是否走 MCP 或其他协议
3. **任务状态同步** - Agent 端任务状态与服务端同步策略
4. **Grasp 调用成本** - task_decompose 中 Grasp 调用的频率和缓存策略
