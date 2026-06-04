# Nexus Interface 架构设计

**版本**: v1.2  
**日期**: 2026-04-02  
**依据**: `nexus-vision.md v2.6`, `00-platform-architecture.md`

---

## 修改履历：
| 日期 | 版本 | 修改人 | 修改内容 |
|------|------|--------|---------|
| 2026-04-02 | v1.2 | 麻子 | 修正 Interface 定位：从"统一界面层"改为"统一 API 网关"，删除 UI 聚合内容，明确 Vigil 为独立服务 |
| 2026-04-02 | v1.1 | 麻子 | 初始版本。Interface 统一界面层架构设计、UI/API/CLI 入口规范。 |
| 2026-04-02 | v1.0 | 麻子 | 初始版本。Interface 统一界面层架构设计、UI/API/CLI 入口规范。 |

---

## 一、Interface 层定位

### 1.1 核心职责

**统一 API 网关（Interface / 网关）**:Nexus 系统的统一 API 入口层，对外提供标准化的访问接口。Interface 不是 UI 聚合平台，各兄弟服务独立拥有自己的用户界面。Interface 的核心职责是统一鉴权、限流、路由和协议转换。

| 职责 | 说明 |
|------|------|
| **API 统一出入口** | 对外提供 RESTful/gRPC/WS API，统一鉴权、限流、监控 |
| **CLI 命令行入口** | 提供命令行工具，便于自动化集成 |
| **协议转换** | 内部五兄弟协议 → 外部标准化协议 |
| **请求路由** | 根据请求类型分发到对应兄弟服务 |
| **鉴权代理** | 调用 Vigil API 进行权限检查和信任分验证 |

### 1.2 设计原则

**原则一：Interface 不是新功能，只是 API 网关**

- 不新增任何业务功能，只是把五兄弟的能力暴露出来
- 所有业务逻辑都在五兄弟内部实现
- Interface 只做路由、鉴权、协议转换

**原则二：统一出入口，多协议支持**

- **RESTful API**:Web 前端、第三方集成
- **gRPC**:高性能内部通信、SDK 生成
- **WebSocket**:实时推送、长连接
- **CLI**:命令行工具、脚本集成
- 所有协议都经过同一套鉴权、限流、监控体系

**原则三：与 Vigil 独立协作，通过 API 调用**

- Vigil 是独立兄弟服务，不属于 Interface
- Interface 通过 Vigil API 进行鉴权
- 统一日志审计、异常检测
- 信任分动态调整 API 访问权限

### 1.3 与五兄弟的关系

```
                    ┌─────────────────┐
                    │   Interface     │
                    │  (API 网关层)     │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
    ┌─────────┐       ┌─────────┐       ┌─────────┐
    │  Grasp  │       │ Reins   │       │   Evo   │
    │  (悟)   │       │  (御)   │       │  (化)   │
    └─────────┘       └─────────┘       └─────────┘
          │                  │                  │
          ▼                  ▼                  ▼
    ┌─────────┐       ┌─────────┐       ┌─────────┐
    │ Reach   │       │ Vigil   │       │  SDK    │
    │  (达)   │       │  (鉴)   │       │         │
    └─────────┘       └─────────┘       └─────────┘

Interface = 五兄弟服务的统一 API 网关
          ≠ UI 聚合平台（各兄弟有独立 UI）
          ≠ 包含 Vigil（Vigil 是独立服务）
```

**关键区别**:

1. **Interface ≠ UI 聚合**:Interface 不提供 UI，各兄弟服务 (Grasp/Reins/Evo/Reach/Vigil/SDK) 各自拥有独立的用户界面
2. **Interface ≠ 包含 Vigil**:Vigil 是独立的安全服务，Interface 通过调用 Vigil 的 API 进行鉴权和审计
3. **Interface 是网关**:作为统一入口，负责路由、鉴权、限流、协议转换

---

## 二、核心功能

### 2.1 API 统一出入口（RESTful/gRPC）

#### 2.1.1 API 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      外部客户端                              │
│  (Web UI / CLI / 第三方应用 / SDK)                           │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Interface Gateway                        │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  API 网关层                                            │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │ │
│  │  │  统一鉴权    │  │  限流控制    │  │  请求日志    │   │ │
│  │  │  (Vigil)    │  │  (Redis)    │  │  (审计)     │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘   │ │
│  └───────────────────────────────────────────────────────┘ │
│                             │                               │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  路由层                                                │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │ │
│  │  │ RESTful  │  │  gRPC    │  │ WebSocket│           │ │
│  │  │  Router  │  │  Router  │  │  Router  │           │ │
│  │  └──────────┘  └──────────┘  └──────────┘           │ │
│  └───────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Grasp API   │   │  Reins API   │   │  Evo API     │
│ (FastAPI)    │   │ (FastAPI)    │   │ (FastAPI)    │
└──────────────┘   └──────────────┘   └──────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Reach API   │   │  Vigil API   │   │  SDK API     │
│ (FastAPI)    │   │ (FastAPI)    │   │ (FastAPI)    │
└──────────────┘   └──────────────┘   └──────────────┘
```

**架构说明**:

- **外部客户端**:包括 Web UI、CLI、第三方应用、SDK 等
- **Interface Gateway**:API 网关层，包含统一鉴权 (Vigil)、限流控制 (Redis)、请求日志 (审计)
- **路由层**:包含 RESTful Router、gRPC Router、WebSocket Router
- **五兄弟服务**:Grasp、Reins、Evo、Reach、Vigil、SDK 各自的 FastAPI 服务

#### 2.1.2 RESTful API 规范

**路径前缀**:

| 模块 | 路径前缀 | 说明 |
|------|----------|------|
| Grasp | `/api/v1/grasp` | 认知管理 API |
| Reins | `/api/v1/reins` | 任务编排 API |
| Evo | `/api/v1/evo` | 进化实验 API |
| Reach | `/api/v1/reach` | 方案市场 API |
| Vigil | `/api/v1/vigil` | 安全审计 API |

**统一响应格式**:

响应包含错误码、消息、业务数据、请求 ID。错误码 0 表示成功，其他错误码按模块分组 (1000-1999 通用错误，2000-2999 Grasp 错误，3000-3999 Reins 错误等)。

**错误码规范**:

- **0**: 成功
- **1000 - 1999**: 通用错误
- **2000 - 2999**: Grasp 错误
- **3000 - 3999**: Reins 错误
- **4000 - 4999**: Evo 错误
- **5000 - 5999**: Reach 错误
- **6000 - 6999**: Vigil 错误

**统一鉴权方式**:

- **Authorization**: Bearer JWT Token
- **X-Agent-Signature**: HMAC 签名

#### 2.1.3 gRPC API 规范

**Proto 文件结构**:

Proto 文件定义服务接口、消息结构。服务接口包括任务管理 (列表、创建、执行) 和流程编排 (编排)。消息结构包括任务 ID、名称、状态、执行 Agent 列表等。

**gRPC 优势**:

- **高性能**:二进制协议，比 RESTful 快 2-3 倍
- **强类型**:Proto 定义接口，自动生成多语言 SDK
- **双向流**:支持实时推送、长连接

#### 2.1.4 WebSocket 实时推送

**订阅主题**:

| 主题 | 说明 | 推送内容 |
|------|------|----------|
| `reins.task.*` | 任务状态变更 | 任务进度、结果 |
| `evo.experiment.*` | 实验状态变更 | 实验进度、指标 |
| `vigil.alert.*` | 安全告警 | 异常检测、越权尝试 |

**WebSocket 协议**:

客户端订阅消息包含类型、主题列表。服务端推送消息包含类型、主题、数据 (事件类型、任务 ID、进度、状态等)。

---

### 2.2 CLI 命令行入口

#### 2.2.1 CLI 工具设计

**命令分组**:

- **认证命令**:login、logout
- **认知管理 (Grasp)**:query、search、list
- **任务管理 (Reins)**:list、create、execute、status
- **进化实验 (Evo)**:create、list、compare
- **方案市场 (Reach)**:list、download、deploy
- **安全审计 (Vigil)**:trust-score、logs、permissions check

#### 2.2.2 CLI 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| **CLI 框架** | Commander.js | Node.js 命令行框架 |
| **HTTP 客户端** | Axios | API 请求 |
| **配置管理** | rc-config | 本地配置文件管理 |
| **输出格式** | Table / JSON | 支持多种输出格式 |
| **进度条** | ora | 加载动画 |

#### 2.2.3 CLI 配置文件

配置文件包含当前配置名称、配置列表 (服务器地址、API Key 等)。支持多环境配置 (production、development 等)。

---

## 三、技术选型

### 3.1 整体技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **API 网关** | Kong / Traefik | 请求路由、限流、鉴权 |
| **RESTful API** | FastAPI (Python) | 高性能、自动 OpenAPI |
| **gRPC Server** | FastAPI + fastapi-grpc | 统一框架，减少技术栈复杂度 |
| **WebSocket** | Socket.io | 实时推送、自动重连 |
| **CLI** | Node.js + Commander.js | 跨平台命令行工具 |
| **认证** | JWT + HMAC | 双重认证 |
| **缓存** | Redis | 会话、限流、热点数据 |
| **日志** | ELK (Elasticsearch + Logstash + Kibana) | 日志收集、分析 |

### 3.2 为什么选择 FastAPI?

**优势**:

- **高性能**:基于 Starlette + Uvicorn，异步处理，比 Flask 快 10 倍
- **自动文档**:自动生成 OpenAPI/Swagger 文档
- **类型检查**:Pydantic + Type Hints，自动数据验证
- **gRPC 支持**:可通过 fastapi-grpc 插件支持 gRPC
- **生态好**:丰富的中间件、插件

### 3.3 为什么选择 Kong/Traefik 作为 API 网关？

| 功能 | Kong | Traefik |
|------|------|---------|
| **请求路由** | ✅ | ✅ |
| **限流** | ✅ | ✅ |
| **鉴权** | ✅ (插件) | ✅ (中间件) |
| **日志** | ✅ | ✅ |
| **监控** | ✅ (Kong Dashboard) | ✅ (Traefik Dashboard) |
| **优势** | 插件生态丰富，社区活跃 | 自动发现配置，K8s 友好 |
| **选择** | **Traefik**(更轻量，配置简单) | |

---

## 四、与五兄弟的集成关系

### 4.1 请求路由逻辑

**路由流程**:

1. 解析请求路径
   - `/api/v1/grasp/*` → Grasp Server
   - `/api/v1/reins/*` → Reins Server
   - `/api/v1/evo/*` → Evo Server
   - `/api/v1/reach/*` → Reach Server
   - `/api/v1/vigil/*` → Vigil Server

2. 鉴权 (Vigil)
   - 检查 JWT Token 有效性
   - 验证 Agent 签名
   - 查询信任分
   - 检查权限矩阵

3. 限流
   - 查 Redis 计数器
   - 超过阈值 → 429 Too Many Requests

4. 路由到对应服务
   - 转发到内部 FastAPI 服务

### 4.2 内部通信协议

**Interface Gateway ↔ 五兄弟服务**:

| 协议 | 场景 | 说明 |
|------|------|------|
| **HTTP/1.1** | 大部分请求 | 兼容性好，调试方便 |
| **gRPC** | 高性能需求 | 如批量查询、实时推送 |
| **WebSocket** | 实时推送 | 任务进度、实验结果推送 |

### 4.3 数据流转示例

**场景：用户查询认知（通过 Web UI）**

1. 用户点击"认知管理"
2. Web UI 调用:GET /api/v1/grasp/query?domain=quantitative_trading
3. Interface Gateway 拦截
   - 鉴权：检查 JWT Token
   - 限流：检查请求频率
   - 路由：转发到 Grasp Server
4. Grasp Server 处理
   - 查 Redis 缓存
   - 未命中 → 查 PostgreSQL
   - 返回认知数据
5. Interface Gateway 返回给 Web UI
6. Web UI 渲染认知列表

**场景：任务执行（通过 CLI）**

1. 用户执行:nexus reins execute task_001
2. CLI 调用:POST /api/v1/reins/execute
3. Interface Gateway 拦截
   - 鉴权：检查 JWT Token + Agent 签名
   - 权限检查:Vigil 检查是否有 execute 权限
   - 路由：转发到 Reins Server
4. Reins Server 执行任务
   - 启动 Agent
   - 监听进度
   - 返回结果
5. Interface Gateway 通过 WebSocket 推送进度
6. CLI 接收进度，实时输出

---

## 五、安全考虑（与 Vigil 配合）

### 5.1 统一鉴权架构

```
┌─────────────────────────────────────────────────────────┐
│                    外部客户端                            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Interface Gateway                      │
│  ┌───────────────────────────────────────────────────┐ │
│  │  第一道：认证（Authentication）                    │ │
│  │  - JWT Token 验证                                  │ │
│  │  - HMAC 签名验证                                   │ │
│  │  - API Key 验证                                    │ │
│  └───────────────────────────────────────────────────┘ │
│                         ▼                               │
│  ┌───────────────────────────────────────────────────┐ │
│  │  第二道：鉴权（Authorization）                     │ │
│  │  - 调用 Vigil check_permission API                 │ │
│  │  - 检查信任分等级                                  │ │
│  │  - 检查权限矩阵                                    │ │
│  └───────────────────────────────────────────────────┘ │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
            请求通过，转发到五兄弟服务
```

### 5.2 与 Vigil 的 API 调用

**鉴权流程**:

1. Interface Gateway 调用 Vigil 权限检查 POST /vigil/permission/check
2. 携带 JWT Token、Agent ID、动作、资源
3. Vigil 返回权限结果 (允许/拒绝、信任等级、信任分)

**日志审计**:

Interface Gateway 自动记录审计日志 POST /vigil/audit_logs，包含请求信息、响应状态、耗时等。

### 5.3 安全最佳实践

| 安全措施 | 实现 | 说明 |
|----------|------|------|
| **HTTPS 强制** | TLS 1.3 | 所有通信加密 |
| **CORS 限制** | 白名单域名 | 防止跨站请求伪造 |
| **CSRF 防护** | SameSite Cookie | 防止跨站请求伪造 |
| **SQL 注入防护** | Parameterized Query | 使用参数化查询 |
| **XSS 防护** | Content-Security-Policy | 前端输出转义 |
| **限流** | Redis + Token Bucket | 防止 DDoS 攻击 |
| **敏感数据脱敏** | Vigil sanitizePayload | 日志、API 响应脱敏 |
| **请求大小限制** | 10MB 上限 | 防止大请求攻击 |

### 5.4 与 Vigil 的协作场景

**场景 1：API 访问权限动态调整**

1. Agent 调用 API → Interface Gateway
2. Interface Gateway 查询 Vigil 信任分
3. Vigil 返回信任分 = 45(受限等级)
4. Interface Gateway 根据权限矩阵拒绝操作
5. 返回错误:Trust score too low, please improve reliability

**场景 2：异常行为实时检测**

1. Interface Gateway 记录所有请求日志
2. Vigil 实时分析日志，发现异常模式
   - 短时间内大量查询 Grasp 认知
   - 尝试访问未授权资源
3. Vigil 触发告警，降低信任分
4. Interface Gateway 实时调整权限

**场景 3：数据脱敏**

1. Agent 上报数据 → Interface Gateway
2. Interface Gateway 调用 Vigil sanitizePayload
3. Vigil 过滤敏感字段 (API Key、密码)
4. 返回脱敏数据到五兄弟服务

---

## 六、实施计划

### 6.1 Phase 1（MVP）

| 任务 | 负责人 | 状态 |
|------|--------|------|
| 实现 Interface Gateway（RESTful 路由 + 鉴权） | 麻子 | ⏳ 待开始 |
| 实现 CLI 基础命令（login、help） | 麻子 | ⏳ 待开始 |
| 集成 Vigil 鉴权 API | 麻子 | ⏳ 待开始 |
| 实现 Grasp / Reins API 路由 | 麻子 | ⏳ 待开始 |

### 6.2 Phase 2（MVP+1）

| 任务 | 负责人 | 状态 |
|------|--------|------|
| 实现 WebSocket 实时推送 | 麻子 | ⏳ 待开始 |
| 实现 gRPC 支持 | 麻子 | ⏳ 待开始 |
| 实现 CLI 完整命令 | 麻子 | ⏳ 待开始 |
| 实现限流、监控 | 麻子 | ⏳ 待开始 |

### 6.3 Phase 3（V1.0）

| 任务 | 负责人 | 状态 |
|------|--------|------|
| API 文档自动生成（Swagger） | 麻子 | ⏳ 待开始 |
| SDK 生成（TypeScript / Python） | 麻子 | ⏳ 待开始 |
| 性能优化（缓存、连接池） | 麻子 | ⏳ 待开始 |
| 安全加固（渗透测试） | 麻子 | ⏳ 待开始 |

---

## 📅 更新日志

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-04-02 | v1.2 | 修正 Interface 定位：从"统一界面层"改为"统一 API 网关"，删除 UI 聚合内容，明确 Vigil 为独立服务 |
| 2026-04-02 | v1.1 | 初始版本。Interface 统一界面层架构设计、UI/API/CLI 入口规范。 |
| 2026-04-02 | v1.0 | 初始版本。Interface 统一界面层架构设计、UI/API/CLI 入口规范。 |

---

*本文档是 Interface 层设计的权威参考。Interface 是统一 API 网关，不是 UI 聚合平台。各兄弟服务 (Grasp/Reins/Evo/Reach/Vigil/SDK) 各自拥有独立的用户界面。Interface 通过与 Vigil API 协作实现统一鉴权和安全控制。实现需严格遵循"统一出入口、多协议支持、与 Vigil 独立协作"三大原则。*
