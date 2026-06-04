# Sprint 64: 系统设置页面 + Nexus-OpenClaw 集成配置

> 版本: v1.0 | 日期: 2026-05-07 | 状态: 待评审

---

## 一、架构背景

### 1.1 Nexus ↔ OpenClaw 映射关系

Nexus 不是独立的系统，而是 OpenClaw 生态中的 **一个用户客户端**。

| Nexus 概念 | OpenClaw 对应 | 说明 |
|-----------|--------------|------|
| Nexus 整体 | OpenClaw 的一个用户 | Nexus 以 "用户" 身份向 OpenClaw 发号施令 |
| 主线程（刚子/CEO） | 一个 OpenClaw session | 指挥调度 session，负责任务分解和协调 |
| 每个 Goal（目标） | 一个独立 OpenClaw session | 专注执行特定目标，有独立上下文 |
| Agent 注册表 | OpenClaw Agent 配置 | 每个 Agent 对应一个 OpenClaw 子代理 |

### 1.2 当前问题

| 问题 | 现状 | 影响 |
|------|------|------|
| 配置分散 | 数据库直接改、代码硬编码、环境变量混用 | 运维困难，新人无法上手 |
| 无可视化 | 没有 UI 管理入口 | 必须靠 DB 脚本或 curl |
| 根智能体未配置化 | 刚子的模型、调度策略写死在代码里 | 换模型/改策略需要改代码 |
| OpenClaw 集成无管理界面 | Session 映射规则、API 连接参数无 UI | 调试集成问题需要查日志 |
| Agent 能力靠手动改 DB | `UPDATE agents SET capabilities = '["coding"]'` | 容易出错 |

---

## 二、目标

| 目标 | 说明 |
|------|------|
| **统一配置入口** | 所有系统级配置集中在 Settings 页面 |
| **Agent 可视化配置** | 在页面上管理 Agent 模型/能力/触发模式 |
| **Nexus-OpenClaw 集成可视化** | 在页面上配置 Session 映射、API 连接 |
| **根智能体可配置** | 刚子（CEO）的模型、调度策略、心跳等可在页面修改 |
| **配置持久化** | 修改后立即写入 DB，重启不丢失 |

---

## 三、页面设计

### 3.1 整体布局

```
┌─────────────────────────────────────────────────────────────────┐
│  系统设置                                                       │
│  ┌─────────┬──────────────────────────────────────────────────┐ │
│  │         │                                                  │ │
│  │ 🧠      │                                                  │ │
│  │ 根智能体 │  [子面板内容]                                      │ │
│  │         │                                                  │ │
│  │ 👥      │                                                  │ │
│  │ Agent   │                                                  │ │
│  │ 配置    │                                                  │ │
│  │         │                                                  │ │
│  │ 🔗      │                                                  │ │
│  │ OpenClaw│                                                  │ │
│  │ 集成    │                                                  │ │
│  │         │                                                  │ │
│  │ ⚙️      │                                                  │ │
│  │ 系统    │                                                  │ │
│  │ 参数    │                                                  │ │
│  │         │                                                  │ │
│  │ 🔒      │                                                  │ │
│  │ 安全    │                                                  │ │
│  └─────────┴──────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 子面板详细设计

#### 面板 1: 🧠 根智能体（CEO）配置

> 管理刚子（orchestrator）的行为配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| Agent ID | 文本 | `gangzi` | 根智能体标识 |
| 模型 | 下拉选择 | `minimax/MiniMax-M2.7-highspeed` | 调度决策用模型 |
| 调度策略 | 下拉选择 | `capability_match` | `capability_match` / `round_robin` / `least_load` |
| 心跳间隔（秒） | 数字 | `300` | 根智能体心跳周期 |
| 任务超时（分钟） | 数字 | `30` | 子任务默认超时 |
| 最大重试次数 | 数字 | `3` | 任务失败自动重试次数 |
| 自动派发 | 开关 | `ON` | 是否自动向子 Agent 派发任务 |
| 调度器 Tick 间隔（秒） | 数字 | `30` | 调度器检查间隔 |

#### 面板 2: 👥 Agent 配置

> 扩展现有的 AgentManagement 页面，增加编辑能力

| 配置项 | 类型 | 说明 |
|--------|------|------|
| Agent 列表 | 表格 | 复用 AgentManagement 的列表 |
| 编辑按钮 | 弹窗 | 点击弹出编辑对话框 |
| 模型 | 下拉选择 | 可选模型列表（从 OpenClaw API 获取） |
| 能力标签 | 多选标签 | 可添加/删除能力标签（coding, testing, ui_migration...） |
| 触发模式 | 下拉选择 | `polling`（主动拉取） / `push`（被动接收） |
| Poll 间隔（秒） | 数字 | 轮询间隔 |
| 最大负载 | 数字 | 最大并发任务数 |
| 状态 | 标签 | 在线/离线（不可编辑，由心跳决定） |
| 注册/注销 | 按钮 | 注册新 Agent / 移除 Agent |

#### 面板 3: 🔗 OpenClaw 集成配置

> 管理 Nexus 与 OpenClaw 的集成参数

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| OpenClaw Gateway URL | 文本 | `http://localhost:8080` | OpenClaw 网关地址 |
| OpenClaw API Token | 密码框 | — | 认证 Token |
| 连接状态 | 状态标签 | 实时检测 | 🟢 已连接 / 🔴 未连接 |
| Session 映射策略 | 下拉选择 | `goal_per_session` | 每个 Goal 一个 session |
| 主线程 Session ID | 文本 | 自动分配 | 根智能体的 session |
| 超时重连（秒） | 数字 | `60` | 连接断开后重连等待 |
| 测试连接 | 按钮 | — | 点击测试 OpenClaw 连接是否正常 |

**Session 映射规则可视化**：

```
OpenClaw Session 映射:

主线程 (刚子) ──────────────────→ session-orchestrator-001
    │
    ├── Goal: Sprint 61 修复 ───→ session-goal-001 (谷子)
    ├── Goal: Sprint 62 执行 ───→ session-goal-002 (麻子)
    └── Goal: Sprint 63 UI ────→ session-goal-003 (扣子)

每创建一个 Goal，自动在 OpenClaw 中创建新 session。
```

#### 面板 4: ⚙️ 系统参数

> Nexus 自身的运行参数

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| 数据库路径 | 文本（只读） | `D:\work\research\agents-nexus\data\reins.db` | 不可修改，仅展示 |
| 后端端口 | 数字 | `8094` | API 服务端口 |
| 前端端口 | 数字 | `5173` | Vite dev server 端口 |
| Worker 地址前缀 | 文本 | `http://localhost:18789/agents/` | Agent 地址模板 |
| 任务调度优先级 | 开关 | `ON` | 是否启用优先级调度 |
| 日志级别 | 下拉选择 | `INFO` | DEBUG / INFO / WARNING / ERROR |
| 数据保留天数 | 数字 | `30` | 心跳日志/任务结果保留天数 |
| 自动清理僵尸任务 | 开关 | `ON` | 启动时自动清理 |
| 离线阈值（分钟） | 数字 | `5` | 超过此时间无心跳标记为离线 |
| 任务回收阈值（分钟） | 数字 | `15` | 离线超过此时间回收任务 |

#### 面板 5: 🔒 安全设置

> 权限和访问控制

| 配置项 | 类型 | 说明 |
|--------|------|------|
| API 认证 | 开关 | 是否启用 API Token 认证 |
| API Tokens 管理 | 列表 | 查看/创建/删除 API Token |
| Agent 操作权限 | 开关组 | 哪些 Agent 可以执行管理操作 |
| 跨域设置 | 列表 | 允许的 CORS 来源 |
| 审计日志 | 列表 | 查看最近的管理操作记录 |

---

## 四、数据库设计

### 4.1 新建表: system_config

```sql
CREATE TABLE IF NOT EXISTS system_config (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,        -- root_agent, agent, openclaw, system, security
    key TEXT NOT NULL,
    value TEXT NOT NULL,           -- JSON 格式存储
    description TEXT,
    updated_at TEXT,
    updated_by TEXT,               -- 'admin' 或 agent_id
    UNIQUE(category, key)
);
```

### 4.2 预置数据

```sql
-- 根智能体配置
INSERT INTO system_config (id, category, key, value, description) VALUES
('cfg-root-001', 'root_agent', 'model', '"minimax/MiniMax-M2.7-highspeed"', '根智能体模型'),
('cfg-root-002', 'root_agent', 'dispatch_strategy', '"capability_match"', '调度策略'),
('cfg-root-003', 'root_agent', 'heartbeat_interval', '300', '心跳间隔(秒)'),
('cfg-root-004', 'root_agent', 'task_timeout_min', '30', '任务超时(分钟)'),
('cfg-root-005', 'root_agent', 'max_retries', '3', '最大重试次数'),
('cfg-root-006', 'root_agent', 'auto_dispatch', 'true', '自动派发'),
('cfg-root-007', 'root_agent', 'scheduler_tick_sec', '30', '调度器tick间隔(秒)');

-- OpenClaw 集成配置
INSERT INTO system_config (id, category, key, value, description) VALUES
('cfg-oc-001', 'openclaw', 'gateway_url', '"http://localhost:8080"', 'OpenClaw网关地址'),
('cfg-oc-002', 'openclaw', 'session_mapping', '"goal_per_session"', 'Session映射策略'),
('cfg-oc-003', 'openclaw', 'reconnect_timeout_sec', '60', '超时重连(秒)');

-- 系统参数
INSERT INTO system_config (id, category, key, value, description) VALUES
('cfg-sys-001', 'system', 'log_level', '"INFO"', '日志级别'),
('cfg-sys-002', 'system', 'data_retention_days', '30', '数据保留天数'),
('cfg-sys-003', 'system', 'auto_cleanup_zombie', 'true', '自动清理僵尸任务'),
('cfg-sys-004', 'system', 'offline_threshold_min', '5', '离线阈值(分钟)'),
('cfg-sys-005', 'system', 'task_recover_threshold_min', '15', '任务回收阈值(分钟)');
```

---

## 五、API 设计

### 5.1 配置管理 API

```
GET    /api/v1/settings                    # 获取所有配置（按 category 分组）
GET    /api/v1/settings/{category}         # 获取某类配置
PUT    /api/v1/settings/{category}/{key}   # 更新单个配置
PUT    /api/v1/settings/{category}/batch   # 批量更新配置
POST   /api/v1/settings/test-connection    # 测试 OpenClaw 连接

GET    /api/v1/settings/models             # 获取可用模型列表（从 OpenClaw API）
GET    /api/v1/settings/sessions           # 获取当前 OpenClaw session 列表
```

### 5.2 响应示例

```json
{
  "root_agent": {
    "model": { "value": "minimax/MiniMax-M2.7-highspeed", "type": "string" },
    "dispatch_strategy": { "value": "capability_match", "type": "select" },
    "heartbeat_interval": { "value": 300, "type": "number" },
    ...
  },
  "openclaw": {
    "gateway_url": { "value": "http://localhost:8080", "type": "string" },
    "connection_status": { "value": "connected", "type": "status" },
    ...
  }
}
```

---

## 六、前端技术选型

| 组件 | shadcn 组件 | 说明 |
|------|------------|------|
| 左侧导航 | 自定义 + Separator | 5 个面板切换 |
| 根智能体配置 | Form + Input + Select + Switch | 表单配置 |
| Agent 配置 | Dialog + Select + Badge | 弹窗编辑 |
| OpenClaw 连接 | Card + StatusIndicator + Button | 状态展示 + 测试按钮 |
| 系统参数 | Form + Input + Switch + Select | 表单配置 |
| 安全设置 | Table + Switch | 列表 + 开关 |
| Toast 通知 | Toast | 操作反馈 |

---

## 七、任务拆分

### Phase 1: 数据库 + API（~0.5 天）

| 任务 | 文件 | 说明 |
|------|------|------|
| 1.1 创建 system_config 表 | migrations/018_system_config.sql | 建表 + 预置数据 |
| 1.2 Settings API | packages/server/src/reins/api/settings.py | CRUD + 测试连接 |
| 1.3 注册路由 | packages/server/src/reins/api/server.py | 挂载 settings router |
| 1.4 模型列表 API | packages/server/src/reins/api/settings.py | 代理 OpenClaw models API |

**Done Criteria**:
- [ ] `system_config` 表创建成功，预置数据插入
- [ ] `GET /api/v1/settings` 返回所有配置
- [ ] `PUT /api/v1/settings/{cat}/{key}` 更新成功
- [ ] `POST /api/v1/settings/test-connection` 返回连接状态
- [ ] `npx tsc --noEmit` 0 errors
- [ ] pytest 通过

### Phase 2: Settings 页面基础框架（~0.5 天）

| 任务 | 文件 | 说明 |
|------|------|------|
| 2.1 Settings 页面路由 | packages/ui/src/pages/Settings.tsx | 左侧导航 + 内容区布局 |
| 2.2 Settings API 服务层 | packages/ui/src/services/settingsApi.ts | 封装所有 API 调用 |
| 2.3 Sidebar 添加入口 | packages/ui/src/components/Sidebar.tsx | 侧边栏增加"系统设置"入口 |
| 2.4 根智能体配置面板 | packages/ui/src/pages/Settings.tsx | 表单 + 保存 |

**Done Criteria**:
- [ ] Settings 页面可访问（http://localhost:5173/settings）
- [ ] 侧边栏有"系统设置"入口
- [ ] 根智能体配置面板显示并加载配置
- [ ] 修改配置后保存成功，刷新页面数据不丢失
- [ ] 页面不白屏，关键元素可见

### Phase 3: Agent 配置面板（~0.5 天）

| 任务 | 文件 | 说明 |
|------|------|------|
| 3.1 Agent 编辑弹窗 | packages/ui/src/pages/Settings.tsx | 模型/能力/触发模式编辑 |
| 3.2 Agent 注册/注销 | packages/ui/src/pages/Settings.tsx | 注册新 Agent 表单 |
| 3.3 能力标签管理 | packages/ui/src/components/Settings/AgentTags.tsx | 添加/删除能力标签 |

**Done Criteria**:
- [ ] 点击 Agent 可弹出编辑对话框
- [ ] 修改模型/能力/触发模式后保存成功
- [ ] 注册新 Agent 后列表刷新
- [ ] 能力标签可动态添加/删除

### Phase 4: OpenClaw 集成面板（~0.5 天）

| 任务 | 文件 | 说明 |
|------|------|------|
| 4.1 OpenClaw 配置表单 | packages/ui/src/pages/Settings.tsx | URL/Token/Session 映射 |
| 4.2 连接测试 | packages/ui/src/pages/Settings.tsx | 测试按钮 + 状态展示 |
| 4.3 Session 映射可视化 | packages/ui/src/components/Settings/SessionMap.tsx | 树状图展示 |
| 4.4 模型列表获取 | packages/ui/src/pages/Settings.tsx | 从 OpenClaw 获取可用模型 |

**Done Criteria**:
- [ ] 配置 Gateway URL + Token 后可保存
- [ ] 点击"测试连接"返回 🟢/🔴 状态
- [ ] Session 映射树状图正确显示
- [ ] 模型下拉列表从 OpenClaw API 获取

### Phase 5: 系统参数 + 安全面板（~0.5 天）

| 任务 | 文件 | 说明 |
|------|------|------|
| 5.1 系统参数面板 | packages/ui/src/pages/Settings.tsx | 端口/日志/清理等配置 |
| 5.2 安全面板 | packages/ui/src/pages/Settings.tsx | API Token 管理/审计日志 |
| 5.3 配置热加载 | 后端 middleware | 配置修改后自动生效（不需要重启） |

**Done Criteria**:
- [ ] 系统参数可修改并保存
- [ ] 日志级别修改后立即生效（不需要重启后端）
- [ ] 安全面板显示 API Token 列表
- [ ] 审计日志可查询

### Phase 6: 回归验证 + 清理（~0.5 天）

| 任务 | 说明 |
|------|------|
| 6.1 全量验证 | 逐个面板手动验证 |
| 6.2 TypeScript 编译 | `npx tsc --noEmit` 0 errors |
| 6.3 构建 | `npm run build` 成功 |
| 6.4 AgentManagement 页面迁移 | 将旧页面整合到 Settings 或保留独立入口 |

---

## 八、Sprint 64 Done Criteria

- [ ] `system_config` 表创建成功，20+ 预置配置项
- [ ] Settings API 全量可用（CRUD + 测试连接 + 模型列表）
- [ ] Settings 页面 5 个子面板全部完成
- [ ] 根智能体配置可在页面修改并持久化
- [ ] Agent 能力/模型/触发模式可在页面编辑
- [ ] OpenClaw 连接配置 + 测试连接功能正常
- [ ] Session 映射树状图可视化
- [ ] 配置修改后热加载（不需要重启后端）
- [ ] `npx tsc --noEmit` 0 errors
- [ ] `npm run build` 成功
- [ ] 页面手动验证：所有面板不白屏，关键交互正常
- [ ] git commit 完整，每个 phase 独立 commit

---

## 九、预期收益

| 指标 | 迁移前 | 迁移后 |
|------|--------|--------|
| 配置方式 | DB 脚本 + 代码硬编码 | 页面可视化配置 |
| 换模型时间 | 改代码 + 重启 | 页面下拉选择，即时生效 |
| Agent 能力管理 | `UPDATE agents SET capabilities` | 页面点击添加标签 |
| OpenClaw 集成调试 | 查日志 + curl | 页面测试连接按钮 |
| 新人上手 | 看代码 + 猜配置 | 看页面一目了然 |
| 运维成本 | 高（分散配置） | 低（集中管理） |
