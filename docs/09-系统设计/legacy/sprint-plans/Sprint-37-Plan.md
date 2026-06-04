# Sprint 37：能力库（MCP 市场）

**日期**: 2026-04-22
**优先级**: P0
**目标**: 建立能力库模块，支持 MCP 注册、浏览、Agent 关联选择

---

## 一、需求背景

- 用户希望有一个 MCP 市场，管理员可以注册新的 MCP Server
- Agent 可以浏览和选择需要的 MCP 能力
- 形成"能力发现 → Agent 选择 → 使用"的闭环

---

## 二、数据模型

### MCP Server 表（mcp_servers）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(36) | 主键 UUID |
| name | VARCHAR(255) | MCP 名称 |
| description | TEXT | 描述 |
| transport | VARCHAR(20) | 传输方式（sse/stdio/streamable）|
| url | TEXT | 连接地址 |
| icon | VARCHAR(255) | 图标 URL |
| category | VARCHAR(50) | 分类（数据/工具/知识库/自动化）|
| status | VARCHAR(20) | active/inactive/testing |
| created_at | DATETIME | 创建时间 |

### MCP Tools 表（mcp_tools）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR(36) | 主键 |
| server_id | VARCHAR(36) | 所属 MCP Server |
| name | VARCHAR(255) | 工具名称 |
| description | TEXT | 工具描述 |
| parameters | JSON | 参数 schema |
| return_type | VARCHAR(50) | 返回值类型 |

~~### Agent-MCP 关联表（agent_mcp_bindings）~~
（不手动关联，改为自动匹配）

---

## 三、任务清单

### Task 37-1：后端 — MCP Server CRUD API + 自动匹配（麻子）

| 端点 | 描述 | 优先级 |
|------|------|--------|
| `GET /api/v1/mcp-servers` | 列出所有 MCP Server（支持分类过滤） | P0 |
| `GET /api/v1/mcp-servers/{id}` | MCP Server 详情 | P0 |
| `POST /api/v1/mcp-servers` | 新增 MCP Server（含工具列表） | P0 |
| `PUT /api/v1/mcp-servers/{id}` | 更新 MCP Server | P1 |
| `DELETE /api/v1/mcp-servers/{id}` | 删除 MCP Server | P1 |
| `GET /api/v1/mcp-servers/{id}/tools` | 列出 MCP 提供的工具 | P0 |
| `POST /api/v1/agents/{id}/match-mcp` | **自动匹配**：根据 Agent 职责描述推荐 MCP | P0 |

**自动匹配逻辑**：
- 输入：Agent 的 `description`（职责描述）
- 匹配：用 MCP 的 `name` + `description` + `tools[].name` + `tools[].description` 做文本相似度匹配
- 输出：按匹配度排序的 MCP 列表（带匹配分数）
- 匹配算法：先用 TF-IDF 关键词匹配，后续可升级 embedding

### Task 37-2：前端 — 能力库页面 + Agent 自动匹配（扣子）

**页面 1：能力库首页（MCP 市场）**
- 路由：`/system/capabilities`
- 卡片式展示所有 MCP Server
- 搜索/分类过滤
- 状态标签（active/inactive）

**页面 2：MCP Server 详情页**
- 路由：`/system/capabilities/{id}`
- 基本信息（名称、描述、URL、transport）
- 工具列表

**页面 3：Agent 编辑页增强**
- 路由：复用 `/system/agents/{id}/edit` 或新建 Agent 时
- 填写职责描述后，**自动触发** `match-mcp` API
- 展示推荐 MCP 列表（按匹配度排序）
- 可选启用/禁用推荐结果

---

## 四、验收标准

### 必做（P0）
- [ ] `GET /api/v1/mcp-servers` 返回 MCP 列表
- [ ] `POST /api/v1/mcp-servers` 成功创建 MCP Server
- [ ] 能力库首页展示 MCP 卡片列表
- [ ] 新增 MCP Server 表单可用
- [ ] MCP 详情页展示工具列表
- [ ] 侧边栏有"能力库"菜单项

### 检验方法
| 检验项 | 方法 | 标准 |
|--------|------|------|
| MCP 列表 API | curl `GET /api/v1/mcp-servers` | 返回 JSON 列表 |
| MCP 创建 API | curl `POST /api/v1/mcp-servers` | 200 + 返回新记录 |
| 能力库页面 | 浏览器打开 `/system/capabilities` | 卡片列表正常渲染 |
| 新增 MCP | 浏览器填写表单提交 | 页面刷新后显示新 MCP |
| 侧边栏菜单 | 打开侧边栏 | "能力库"可见可点击 |

---

## 五、执行顺序

```
1. Task 37-1（后端 API + 数据库，基础）
2. Task 37-2（前端页面，依赖后端 API）
3. 浏览器端到端验证
```

---

*创建时间: 2026-04-22 22:13*
*创建人: 刚子*
