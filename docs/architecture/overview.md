# 架构概览

Nexus 是一个 AI Agent 团队协作编排框架，采用**五域分离**的微服务架构。每个域独立演进，通过共享服务层协作。

## 整体架构

Nexus 采用四层分层架构：

```
┌──────────────────────────────────────────────────────┐
│ 统一界面层 (Unified Interface Layer)                  │
│  React Frontend │ REST API │ CLI                     │
├──────────────────────────────────────────────────────┤
│ 协作编排层 (Orchestration Layer)                      │
│  Workflow Engine │ A2A Hub │ Task Scheduler           │
├──────────────────────────────────────────────────────┤
│ Agent 执行层 (Agent Execution Layer)                  │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐            │
│  │认知 │ │驾驭 │ │进化 │ │拓展 │ │安全 │            │
│  │GrASP│ │Reins│ │ Evo │ │Reach│ │Vigil│            │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘            │
├──────────────────────────────────────────────────────┤
│ 基础设施层 (Infrastructure Layer)                     │
│  SQLite/PostgreSQL │ EventBus │ Auth │ Common        │
└──────────────────────────────────────────────────────┘
```

**分层原则：**
- 各层之间通过标准接口通信
- 下层为上层提供服务，上层调用下层能力
- 层与层之间保持松耦合，便于独立演进

## 五域架构

### 1. 🧠 认知域 (GrASP)

**职责**：知识提取、认知评估、文档注入、GraphRAG 检索。

**核心流程**：
```
文档/结果 → 解析器 → 认知提取 → 认知存储 → 任务上下文注入
                                      ↓
                              GraphRAG 检索后端
```

**关键组件**：
| 组件 | 目录 | 职责 |
|------|------|------|
| 解析器注册表 | `parser/` | 文档解析器（Markdown 等）注册与调度 |
| 认知提取 | `analysis/` | 从文本中提取结构化认知 |
| 后端注册 | `registry/` | 后端注册（Memory、Microsoft GraphRAG） |
| 知识注入 | `injection/` | 将认知注入到任务上下文 |
| 适配器 | `adapters/` | GraphRAG 后端适配器 |

**API 端点**：`/api/v1/grasp/`

### 2. 🎯 驾驭域 (Reins)

**职责**：目标→工程→任务分解、Agent 调度、人机协作 (HITL)、任务执行追踪。

**核心流程**：
```
Goal → Projects → Tasks → Agent 匹配 → 执行 → 验证 → 完成/争议
                                      ↓
                              HITL 人工审批
```

**关键组件**：
| 组件 | 目录 | 职责 |
|------|------|------|
| 状态机 | `core/` | Goal/Project/Task 状态机 |
| 调度器 | `scheduler/` | Agent 匹配、任务分配、负载均衡 |
| 追踪器 | `tracking/` | 执行追踪、超时处理 |
| 消息 | `messaging/` | 命令、事件发布 |
| NexusLog | `nexus_log/` | 执行日志与追踪 |

**API 端点**：`/api/v1/goals/`、`/api/v1/projects/`、`/api/v1/tasks/`、`/api/v1/agents/`

### 3. 🧬 进化域 (Evo)

**职责**：从历史任务中蒸馏知识、更新 Agent 能力权重。

**核心流程**：
```
已完成任务 → 基因提取 → 胶囊生成 → 权重更新
              ↓
        知识胶囊存储
```

**关键组件**：
| 组件 | 目录 | 职责 |
|------|------|------|
| 蒸馏引擎 | `distillation/` | 从任务中提取 Gene，聚合成 Capsule |
| 突变引擎 | `mutation/` | 知识变异与优化 |
| A2A 传递 | `a2a/` | Agent-to-Agent 知识传递 |
| 权重管理 | `weight/` | Agent 能力权重更新 |

**API 端点**：`/api/v1/evo/`

### 4. 🔌 拓展域 (Reach)

**职责**：场景库管理、行业包实例化、技能注册。

**核心流程**：
```
场景模板 → 实例化 → 自动生成 Goal/Project/Task 树
                    ↓
            行业包匹配 + 能力标签
```

**关键组件**：
| 组件 | 目录 | 职责 |
|------|------|------|
| 场景库 | `scenarios/` | 场景 CRUD 与实例化 |
| 行业包 | `industry/` | 行业标签与包管理 |
| MCP | `mcp/` | Model Context Protocol 集成 |
| 产物 | `artifacts/` | 任务产物管理 |
| 附件 | `attachments/` | 统一附件系统 |

**API 端点**：`/api/v1/scenarios/`、`/api/v1/industry-packs/`

### 5. 🛡️ 安全域 (Vigil)

**职责**：信任管理、争议裁决、安全门禁、降级策略。

**核心流程**：
```
争议任务 → 人工裁决中心 → 批准/拒绝/要求修改
              ↓
        信任度更新 + 能力标签调整
```

**关键组件**：
| 组件 | 目录 | 职责 |
|------|------|------|
| 信任管理 | `trust/` | Agent 信任度计算 |
| 访问控制 | `access/` | RBAC 权限控制 |
| 安全告警 | `alerts/` | 异常检测与告警 |

**API 端点**：`/api/v1/vigil/`、`/api/v1/human-review/`

## 公共服务

| 服务 | 位置 | 职责 |
|------|------|------|
| Database | `shared/database/` | DB 连接池、基类、Alembic 迁移 |
| EventBus | `shared/eventbus/` | 事件发布/订阅、SSE 推送 |
| Auth | `shared/auth/` | JWT 认证、RBAC |
| Common | `shared/common/` | 通用工具、类型定义 |
| Exception | `shared/exception/` | 统一异常处理、错误码 |
| Logging | `shared/logging/` | NexusLog 日志引擎 |

## 数据模型

### 核心实体

```
Goal (1) ──→ Project (N) ──→ Task (N)
  │              │              │
  │ 战略目标      │ 工程项目      │ 执行任务
  │              │              ↓
  │              │        Agent (M:N)
  │              │              ↓
  │              │        Execution Record
  │              │              ↓
  │              │        Verification Result
  │              │              ↓
  │              │        HITL Review (optional)
  │              │
  ↓              ↓
mode:          depends_on:
  - normal       - JSON 数组
  - exploration  - 任务依赖关系
```

### Agent 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | VARCHAR(32) | Agent 唯一标识 |
| `name` | VARCHAR(255) | Agent 名称 |
| `status` | VARCHAR(20) | 在线状态（online/busy/offline） |
| `load` | INTEGER | 当前负载百分比 |
| `capability_tags` | JSON | 能力标签字典 |
| `model_name` | VARCHAR(255) | 使用的模型名称 |
| `platform_type` | VARCHAR(50) | 平台类型（hermes/openclaw/...） |

### Task 状态机

```
todo → pending → in_progress → done
  │        │          │
  │        ↓          ↓
  │    review_needed  failed
  │        │          │
  │        ↓          ↓
  │    verifying   disputed
  │        │
  └────────┘
      (自动分配 Agent 后进入 in_progress)
```

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + TypeScript + Vite + shadcn/ui + React Router |
| 后端 | Python 3.12+ + FastAPI + SQLAlchemy (async) |
| 数据库 | SQLite（开发默认）/ PostgreSQL（生产推荐） |
| 迁移 | Alembic |
| 部署 | Docker Compose |

## 关键设计决策

| 编号 | 决策 | 内容 |
|------|------|------|
| D1 | 领域模型 | Goal-Project-Task = 战略:项目:战术，1:N:N |
| D2 | Task 状态 | review_needed/verifying/disputed 是真实业务状态 |
| D3 | Agent 缓存 | 去掉内存缓存，只用 DB |
| D4 | 迁移工具 | 统一 Alembic，废弃手动 SQL 迁移 |
| D5 | 推送式执行 | Nexus 主动派发任务，不依赖外部 Worker |
| D6 | 三层质量门 | 编译通过 → API 200 → 页面渲染 → DB 数据正确 |
